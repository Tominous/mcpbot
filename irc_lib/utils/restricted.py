def restricted(f):
    def warp_f(*args):
        bot    = args[0]
        sender = args[1]
        chan   = args[2]
        status      = bot.getStatus(sender)
        whitelisted = sender in bot.whitelist
        if not whitelisted or int(status) != 3:
            if chan:
                bot.say(chan, '%s tried to use a restricted command.'%sender)
            bot.say(sender, 'You do not have the right to do that')
            return
        f(*args)
    return warp_f
