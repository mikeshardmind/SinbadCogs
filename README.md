# SinbadCogs
[![Code style: black](https://github.com/mikeshardmind/SinbadCogs/workflows/black/badge.svg)](https://github.com/ambv/black) 
[![Type Checked with mypy](https://github.com/mikeshardmind/SinbadCogs/workflows/mypy/badge.svg)](https://github.com/python/mypy) 
[![Red](https://img.shields.io/badge/Red-DiscordBot-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop) 


## Availability of Support

Support is available for bugs and feature requests only.

Support for usage issues is outside of what I currently have time or prioritization for.


## Whats here?

Various addons for Red Discordbot. Most of these are focused around utility purposes.


### AntiMentionSpam

This cog provides automated actions against people spamming mentions.

Configuration is available via the `antimentionspam` command.


### BanSync

This cog provides a few functions for handling bans across multiple servers.

More help is available via `help BanSync`


### ChannelRedirect

This cog can lock commands down to specific channels, with exceptions.

This cog does not disable or otherwise interfere with licenseinfo.

### EmbedMaker

This cog provides a means to create, store, and send embedded messages from the bot.

Full documentation is still pending,
but a robust example is available
[here](https://gist.github.com/mikeshardmind/0e15779370d7761a8608ce94936721ed) for now

### GuildJoinRestrict

Allows controlling and logging which guilds the bot can join based on configurable settings
and either an allowlist or blocklist.

Tip: If you do not want the bot taking these actions automatically,
or just want a log of guilds the bot has joined, set up a discord log channel,
use the allowlist mode with an empty allowlist, and do not turn on autoleaving.

### MentionHelp

This cog provides people who mention the bot a bit of assistance
in finding the help command and a valid prefix should they need it.

### ModOnlyMode

This cog is for locking a bot's usage to mods and admins (on a per sever basis).

This cog does not disable or otherwise interfere with licenseinfo.

### QuoteTools

Provides a quick way to reference other messages without needing to jump to them to view.

### Relays

Mirror messages sent in a channel to other channels.

### RoleManagement

Provides:

 - Reaction roles
 - Self roles
 - Purchasable roles
 - User list data based on roles
 - Mass Role modifications
 
Note: Roles self assigned via reaction or command are subject to
the settings configured in the `roleset` command.

This cog has some additional information documented [here](rolemanagement/README.md)

### RoomTools

Provides two seperate ways to allow users to create temporary channels.

For command based temporary voice channels, see the `tempchannelset` command

For temporary channels generated automatically, see the `autoroomset` command


### RSS

Periodic RSS updates to channels.

For more information, use `help RSS`


### Scheduler

Allows scheduling commands. 

For more information, use `help Scheduler`


## What about the other cogs not listed here?

Use at your own risk, they are disabled, hidden, undocumented,
or intended to be replaced by newer alternatives.

They aren't designed to actively cause harm, but I'm not advertising them.

## Why weren't you working on this/as invested in this anymore?

Significant personal disagreements which led to wanting to have nothing to do with Red's community.

## Why are you working on this again?

Two communities that I work closely with would like to continue using Red for now.
I am being paid for my time spent supporting the needs of these communities.

## Custom forks

Read the license, but disallowed.

I previously attempted to keep this more permissive while protecting my own time,
it took less than a day from that attempt for this to need to be solved more strongly.

## Code re-use

Again, read the license.

The cliff notes in plain English:

Generally, if you're modifying for personal use privately, it's allowed.
Taking portions of the code which have general utility not specific to the cog
is allowed with proper attribution of source.
Modifying the code and maintaining a fork is not allowed.
Attaching monetization to this code specifically is not allowed.

While the above attempts to be accurate, the language of the license takes precedence and
is only provided to help rule out disallowed usage prior to reading in full.
