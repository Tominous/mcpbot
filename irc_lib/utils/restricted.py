def restricted(level=4):
    def wrap(f):
        def wrap_f(*args, **kwargs):
            commands = args[0]
            bot = commands.bot
            sender = commands.ev.sender
            chan = commands.ev.chan

            # Small work around for !pub restricted commands
            if sender == chan:
                whitelisted = True
                status = 3
                usrlevel = 4
            else:
                status = bot.getStatus(sender)
                whitelisted = sender in bot.whitelist
                if sender in bot.whitelist:
                    usrlevel = bot.whitelist[sender]
                else:
                    usrlevel = 0

            # Official auth check
            if not whitelisted or status != 3 or level > usrlevel:
                if chan:
                    bot.say(chan, '%s tried to use a restricted command.' % sender)
                bot.say(sender, 'You do not have the rights to do that')
                return

            f(*args, **kwargs)
        return wrap_f
    return wrap
