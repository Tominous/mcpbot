def get_nick(name):
    if name[0] == ':': name = name[1:]
    return name.split('!')[0]
