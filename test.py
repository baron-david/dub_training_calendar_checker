data = {
    '2026-09-09': [{'time': '2026-09-09T19:00:00-0700', 'slotsAvailable': 3}],
    '2026-09-10': [{'time': '2026-09-10T19:00:00-0700', 'slotsAvailable': 1}],
    '2026-09-11': [{'time': '2026-09-11T19:00:00-0700', 'slotsAvailable': 2}],
    '2026-09-14': [
        {'time': '2026-09-14T17:00:00-0700', 'slotsAvailable': 1},
        {'time': '2026-09-14T19:00:00-0700', 'slotsAvailable': 4},
    ],
    '2026-09-15': [{'time': '2026-09-15T18:00:00-0700', 'slotsAvailable': 2}],
    '2026-09-16': [
        {'time': '2026-09-16T17:00:00-0700', 'slotsAvailable': 3},
        {'time': '2026-09-16T19:00:00-0700', 'slotsAvailable': 3},
    ],
}

new_times = {
    '2026-09-16T17:00:00-0700', '2026-09-15T18:00:00-0700',
    '2026-09-10T19:00:00-0700',
}


filtered = {
    date: [slot for slot in slots if slot['time'] in new_times]
    for date, slots in data.items()
}

filtered = {}
for date, slots in data.items():
    kept_slots = []
    for slot in slots:
        if slot['time'] in new_times:
            kept_slots.append(slot)
    filtered[date] = kept_slots

# drop dates that end up with an empty list after filtering
filtered = {date: slots for date, slots in filtered.items() if slots}

print(filtered)