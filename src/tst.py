import timeit
import random

# Original implementation
def transpose_to_scale_original(notes, scale):
    if len(scale) != 12:
        raise ValueError("Scale must be 12 notes long")

    def transpose_note(note):
        scale_degree = note % 12
        for i in range(12):
            if scale[(scale_degree + i) % 12] == 1:
                return note + i

    return [transpose_note(note) for note in notes]

# New implementation
def transpose_to_scale_new(notes, scale):
    if len(scale) != 12:
        raise ValueError("Scale must be 12 notes long")

    def transpose_note(note):
        scale_degree = note % 12
        if scale[scale_degree] == 1:
            return note
        for i in range(1, 7):
            if scale[(scale_degree + i) % 12] == 1:
                upper_match = note + i
                break
        for i in range(1, 7):
            if scale[(scale_degree - i) % 12] == 1:
                lower_match = note - i
                break
        return upper_match if abs(upper_match - note) <= abs(lower_match - note) else lower_match

    return [transpose_note(note) for note in notes]

# Benchmark function
def run_benchmark(func, scale, num_notes, num_runs):
    notes = [random.randint(0, 127) for _ in range(num_notes)]
    return timeit.timeit(lambda: func(notes, scale), number=num_runs)

# Setup
scale = [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0]  # C minor pentatonic
num_runs = 10000
note_counts = [4, 10, 100, 1000]

# Run benchmarks
print("Benchmarking results:")
print(f"{'Input Size':>12} {'Original (s)':>15} {'New (s)':>15} {'Ratio (New/Original)':>25}")
for num_notes in note_counts:
    time_original = run_benchmark(transpose_to_scale_original, scale, num_notes, num_runs)
    time_new = run_benchmark(transpose_to_scale_new, scale, num_notes, num_runs)
    ratio = time_new / time_original
    print(f"{num_notes:12d} {time_original:15.6f} {time_new:15.6f} {ratio:25.6f}")
    
    
input("enter to exit")