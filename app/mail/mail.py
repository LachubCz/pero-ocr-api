from drymail import SMTPMailer, Message


def send_mail(subject, body, sender, password, recipients, host):
    client = SMTPMailer(host=host, user=sender[1], password=password, tls=True)
    message = Message(subject=subject, sender=sender,
                      receivers=recipients, html=body)
    client.send(message)
