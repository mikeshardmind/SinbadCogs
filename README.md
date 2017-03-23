# SinbadCogs

Slowly growing collection of cogs for [Red](https://github.com/Twentysix26/Red-DiscordBot)

I'm Sinbad#0413 on Discord


# Announcer

Cog for server owners to broadcast to a specific manual set of channels

# CrossQuote

Cog for quoting from any server the bot is in by just the message ID
Cog respects server privacy settings, and defaults to less permissive.

# Embedder

Cog for Making, Storing, and calling Embed objects to the chat.
Embeds are unique to each server
Globally accessible embeds may be added at some point later
Note: If a user has link previews disabled, they also do not see embeds.

# Serverblacklist

Configureable cog for maintaining a list of servers the bot will leave when invited to
Optionally you can set a message to send to the default server channel to explain this.

# tempchannels

Configureable cog for allowing the creation of temporary voice channels
Temporary channels, when enabled, last for 5 minutes if unused, or dissapear immediately
when they become empty after having been joined.

Optional setting to allow the creator of the temporary channel to own the settings of that channel.

Warning:
This does not respect the permissions of the person calling it, it is specifically designed to bypass
needing to grant "manage channels" to people for them to create short lived voice chats.
It requires that someone who can manage channels enable it for the server.

