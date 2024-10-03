PATTERN = -1
CHROMATIC = 0
MINOR = 1
MAJOR = 2
DORIAN = 3
PHRYGIAN = 4
LYDIAN = 5
MIXOLYDIAN = 6
LOCRIAN = 7
HARMONIC_MINOR = 8
MELODIC_MINOR = 9
WHOLE_TONE = 10
DIMINISHED = 11
AUGMENTED = 12
MAJOR_PENTATONIC = 13
MINOR_PENTATONIC = 14
BLUES = 15
JAPANESE = 16
EGYPTIAN = 17
GYPSY = 18
SPANISH = 19
FREYGISH = 20


SCALES = {
    PATTERN: {"name": "PATTERN",
              "indices": None},
    CHROMATIC:
        {"name": "CHROMATIC",
         "indices": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]},
    MINOR:
        {"name": "MINOR",
         "indices": [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0]},
    MAJOR:
        {"name": "MAJOR",
         "indices": [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]},
    DORIAN:
        {"name": "DORIAN",
         "indices": [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0]},
    PHRYGIAN:
        {"name": "PHRYGIAN",
         "indices": [1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0]},
    LYDIAN:
        {"name": "LYDIAN",
         "indices": [1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1]},
    MIXOLYDIAN:
        {"name": "MIXOLYD.",
         "indices": [1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0]},
    LOCRIAN:
        {"name": "LOCRIAN",
         "indices": [1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0]},
    HARMONIC_MINOR:
        {"name": "HARM. MIN",
         "indices": [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1]},
    MELODIC_MINOR:
        {"name": "MEL. MIN",
         "indices": [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1]},
    WHOLE_TONE:
        {"name": "WHOLE TN.",
         "indices": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]},
    DIMINISHED:
        {"name": "DIMINISH.",
         "indices": [1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1]},
    AUGMENTED:
        {"name": "AUGMENTED",
         "indices": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]},
    MAJOR_PENTATONIC:
        {"name": "PENTA MAJ",
         "indices": [1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0]},
    MINOR_PENTATONIC:
        {"name": "PENTA MIN",
         "indices": [1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0]},
    BLUES:
        {"name": "BLUES",
         "indices": [1, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0]},
    JAPANESE:
        {"name": "JAPANESE",
         "indices": [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0]},
    EGYPTIAN:
        {"name": "EGYPTIAN",
         "indices": [1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1]},
    GYPSY:
        {"name": "GYPSY",
         "indices": [1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0]},
    SPANISH:
        {"name": "SPANISH",
         "indices": [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0]},
    FREYGISH:
        {"name": "FREYGISH",
         "indices": [1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0]}
}
