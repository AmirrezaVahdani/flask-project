from flask_socketio import Namespace

class PublicDashboardNamespace(Namespace):
    # اضافه کردن *args و **kwargs برای پذیرش هرگونه آرگومان ورودی از سمت کلاینت
    def on_connect(self, *args, **kwargs):
        # حذف پرینت فارسی مستقیم برای جلوگیری از خطای Unicode در ویندوز
        print("--> A monitor/browser connected to the public real-time dashboard.")

    def on_disconnect(self, *args, **kwargs):
        print("--> Public monitor disconnected.")