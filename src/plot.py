import matplotlib.pyplot as plt

def plot(count_per_pids: dict[set[int], int], output: str):
  ax = plt.gca()

  sorted_counts = sorted(count_per_pids.items(), key=lambda x: x[1], reverse=True)

  bar_for_pid = {}
  offset = 0
  for pids, count in sorted_counts:
    for pid in pids:
      bar_for_pid.setdefault(pid, []).append([offset, count])
    offset += count

  sorted_pids = sorted(bar_for_pid.keys(), reverse=True)
  for i, pid in enumerate(sorted_pids, 1):
    bars = bar_for_pid[pid]
    ax.broken_barh(bars, (i - 0.5, 1), facecolors=f'C{i}', edgecolor='black')

  ax.set_yticks(range(1, len(sorted_pids) + 1), labels=sorted_pids)

  plt.savefig('plot.png')
  plt.show()
