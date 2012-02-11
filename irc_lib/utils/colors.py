#Short hand to IRC
S2I = {
    '$B': '\x02',
    '$U': '\x1f',
    '$R': '\x16',
    '$N': '\x0f',
    '$C': '\x03',
}


def conv_s2i(text):
    out_text = text
    for code, char in S2I.items():
        out_text = out_text.replace(code, char)
    return out_text
