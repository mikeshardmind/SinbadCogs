# SinbadCogs
[![Code style: black](https://github.com/mikeshardmind/SinbadCogs/workflows/black/badge.svg)](https://github.com/ambv/black) 
[![Type Checked with mypy](https://github.com/mikeshardmind/SinbadCogs/workflows/mypy/badge.svg)](https://github.com/python/mypy) 
[![Red](https://img.shields.io/badge/Red-DiscordBot-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop) 


## Availability of Support

I was supporting these cogs more thoroughly before, going forward,
I'll be providing some support, but new features are unlikely.

If you find a bug or security issue, feel free to reach out, new features aren't being added.

I will not be removing the cogs here, people are still using them and I see no good reason to do so.


## Whats here?

Various addons for Red Discordbot. Most of these are focused around utility purposes.


### AntiMentionSpam

This cog provides automated actions against people spamming mentions.

Configuration is available via the `antimentionspam` command.


### BanSync

This cog provides a few functions for handling bans across multiple servers.

More help is available via `help BanSync`


### EmbedMaker

This cog provides a means to create, store, and send embedded messages from the bot.

Full documentation is still pending,
but a robust example is available
[here](https://gist.github.com/mikeshardmind/0e15779370d7761a8608ce94936721ed) for now

### GuildBlacklist

Allows blacklisting guilds by ID or the owner's ID

### GuildWhitelist

Allows whitelisting guilds by ID or the owner's ID

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

Use at your own risk, they are disabled or hidden due to me not feeling they are ready for use.


## Why weren't you working on this/as invested in this anymore?

See [this](why_no_support.md)


## Why are you working on this again?

Two communities that I work closely with would like to continue using Red for now.
I am being paid for my time spent supporting the needs of these communities.

## Custom forks

While the license intentionally allows custom forks, if you fork these cogs to make changes intended for use as a fork, please take the time to ensure the following changes

1. Update the info.json to note that it is a modification and add yourself to the author list.
2. If you modify the way in which data is stored, please create a new config object with a seperate unique id. This includes changing how data is accessed (different key) changing what data is stored in a way different to how I stored it, deleting data which is stored, and anything else which would break a user switching from my repo, to your fork, and then back.
3. Add something to the cog help text to make it clear that it is a modification.

This is a very short list of requests to ensure I don't end up being support for your modifications (if you want your modifications to be supported, convince me they belong via issue)

Assuming these requests are abided by,
you may take this section of the Readme as explicit consent for modification under
Red's Cogboard rules. (sepcifically pertaining to "Do not ask for a developer to modify another developer’s code, cog, or source without their explicit permission.")
