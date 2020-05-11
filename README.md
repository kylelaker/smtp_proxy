# SMTP Proxy

Proxies a message from an SMTP client to an SMTP server. This is useful for things like
[Lexmark printers](https://kylelaker.com/2020/04/25/smtp-truncate.html) that don't know how to
properly authenticate to an SMTP server if the password is longer than 31 characters.

This will accept messages and forward them to the remote server. This should _NEVER_ be run on a
server that is publicly accessible. It doesn't really do any sort of authentication and you will
almost certainly act as an open relay which would be pretty bad.
