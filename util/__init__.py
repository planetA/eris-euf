def pretty_print(items):
    s_items = sorted(items)
    last = s_items[0]
    ranges = [[last]]
    for i in items[1:]:
        if i == last+1:
            ranges[-1].append(i)
        else:
            ranges.append([i])

        last = i

    subs = []
    for r in ranges:
        if len(r) == 1:
            subs.append(str(r[0]))
        else:
            subs.append(str(r[0]) + "-" + str(r[-1]))

    return ",".join(subs)
