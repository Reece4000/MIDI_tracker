cdef list note_base_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-', 'OFF']
cdef int timeline_length = 999
cdef int num_timeline_rows = 20


def midi_to_note(int midi_note):
    cdef int octave
    cdef int note_index
    cdef str note_name
    cdef str return_val

    if midi_note == -1:
        return 'OFF'

    else:
        octave = (midi_note //12) -1
        note_index = midi_note % 12
        note_name = note_base_names[note_index]
        return f"{note_name}{octave}"


def cy_get_timeline_step_state(int y, str track_type, int song_cursor, int phrase_cursor,
                               int song_playhead, int phrase_playhead, int page, list song_steps, 
                               list cursor_phrase, bint is_playing):
    cdef int mid
    cdef int cursor_pos
    cdef int offset
    cdef int step_index
    cdef int step_num
    cdef str text
    cdef tuple text_color
    cdef bint condition
    cdef tuple cursor

    mid = num_timeline_rows // 2 - 1
    cursor_pos = song_cursor if track_type == "song" else phrase_cursor
    offset = -min(mid, cursor_pos) if cursor_pos <= mid else -mid
    if cursor_pos > timeline_length - mid:
        offset -= mid - (timeline_length - cursor_pos)


    step_index = cursor_pos + y + offset
    if track_type == "song":
        if song_steps[step_index] is not None:
            step_num = song_steps[step_index]
        else:
            step_num = -1 
    else:
        if cursor_phrase[step_index] is not None:
            step_num = cursor_phrase[step_index]
        else:
            step_num = -1 


    if step_index < 0 or step_index >= timeline_length:
        text, text_color = "", (-1, -1, -1)
    else:
        if track_type == "song":
            condition = (step_index == song_playhead and is_playing)
        else:
            condition = (step_index == phrase_playhead and is_playing) and (song_playhead == song_cursor)

        text_color = (0, 255, 0) if condition else (255, 255, 255)

        # Fixing the string formatting issue
        text = "{:0>3}".format(step_num) if step_num >= 0 else ' - - '

    cdef tuple bg = (12, 24, 24) if not y % 2 else (2, 6, 6)
    cdef int page_check = 0 if track_type == "song" else 1

    if page == page_check and step_index == cursor_pos:
        cursor = (250, 220, 0)
    elif step_index == cursor_pos:
        cursor = (140, 140, 0)
    else:
        cursor = (0, 0, 0)

    cdef list return_list = [text, text_color, cursor, bg]
    return return_list


