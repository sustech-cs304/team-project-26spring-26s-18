import yagmail

class MailUtil:
    USER = "17692267492@163.com"
    PASSWORD = "FPenjCLUPk5Rxy5Y"
    HOST = "smtp.163.com"
    PORT = 465

    @staticmethod
    def send_email(to: str, subject: str, content: str):
        yag = yagmail.SMTP(user=MailUtil.USER, password=MailUtil.PASSWORD, host=MailUtil.HOST, port=MailUtil.PORT, smtp_ssl=True)
        yag.send(to=to, subject=subject, contents=content)
