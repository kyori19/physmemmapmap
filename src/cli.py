from argparse import ArgumentParser
from os import execvp, getgid, getuid, setgid, setuid
from sys import orig_argv

from psutil import NoSuchProcess, Process
from pyprctl import Cap, CapState, get_keepcaps, set_keepcaps

from plot import plot


class CLIException(Exception):
  pass


def parse_args():
  parser = ArgumentParser(
    description='Visualize physical memory usage across forked processes',
  )
  parser.add_argument(
    'pid',
    nargs='*',
    type=int,
    help='process ids for target processes.',
  )
  parser.add_argument(
    '-e', '--exact',
    action='store_true',
    help='stop including subprocesses to the result. (default: false)',
  )
  parser.add_argument(
    '-p', '--pathname',
    nargs=1,
    default=None,
    help='filter memory maps by pathname. (default: None)',
  )
  parser.add_argument(
    '-o', '--output',
    nargs=1,
    default=['plot.png'],
    help='output file path for the plot. (default: plot.png)',
  )
  parser.add_argument(
    '--fixed-width',
    nargs=1,
    type=int,
    default=None,
    help='fixed width for the memory plot. (default: not fixed)',
  )
  parser.add_argument(
    '--no-sudo',
    action='store_true',
    help='stop using sudo to gain permissions. (default: false)',
  )
  return parser.parse_args()


def get_procs(input: list[int], exact: bool) -> list[Process]:
  try:
    procs = list(map(Process, input))
  except NoSuchProcess as e:
    raise CLIException(f'PID {e.pid} does not exist')

  if exact:
    return procs

  if len(procs) == 0:
    procs.append(Process())

  for proc in procs.copy():
    procs.extend(proc.children(recursive=True))

  return procs


def get_ugid(procs: list[Process]) -> tuple[int, int]:
  if len(procs) == 0:
    raise CLIException('No process specified')

  uid, _, _ = procs[0].uids()
  gid, _, _ = procs[0].gids()

  invalid = next(filter(lambda proc: proc.uids()[0] != uid and proc.gids()[0] != gid, procs[1:]), None)
  if invalid:
    raise CLIException(f'All processes must have same UID and GID, {procs[0].pid} and {invalid.pid} does not.')

  return uid, gid


def sudo(no_sudo: bool):
  if no_sudo:
    raise CLIException('insufficient permissions, cannot continue.')

  print('insufficient permissions, re-running via sudo.')
  args = orig_argv.copy()
  args.append('--no-sudo')
  execvp('sudo', args)


def get_capabilities(tuid: int, tgid: int, no_sudo: bool):
  cuid = getuid()
  cgid = getgid()
  caps = CapState.get_current()

  caps_changed = False

  if tuid != cuid and Cap.SETUID not in caps.effective:
    caps.effective.add(Cap.SETUID)
    caps_changed = True

  if tgid != cgid and Cap.SETGID not in caps.effective:
    caps.effective.add(Cap.SETGID)
    caps_changed = True

  if Cap.SYS_ADMIN not in caps.effective:
    caps.effective.add(Cap.SYS_ADMIN)
    caps_changed = True

  if caps_changed:
    try:
      caps.set_current()
      print(caps)
    except PermissionError:
      sudo(no_sudo)

  if tgid != cgid:
    # change gid first because setuid clears all effective caps
    setgid(tgid)

  if tuid != cuid:
    if tuid != 0 and not get_keepcaps():
      set_keepcaps(True)

    setuid(tuid)

    if tuid != 0:
      # recover CAP_SYS_ADMIN cleared by setuid
      caps.get_current()
      caps.effective.add(Cap.SYS_ADMIN)
      caps.set_current()


def pmmm():
  try:
    args = parse_args()
    procs = get_procs(args.pid, args.exact)
    ugid = get_ugid(procs)
    get_capabilities(*ugid, args.no_sudo)

    plot(procs, args.pathname[0] if args.pathname else None, args.output[0], args.fixed_width[0] if args.fixed_width else None)
  except CLIException as e:
    print(f'Error: {e.args[0]}')
    exit(1)
