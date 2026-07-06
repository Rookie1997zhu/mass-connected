from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.contract.models import NdaTemplate

DEFAULT_NDA_BODY = """本保密协议（以下简称「本协议」）由 **（客户公司名称）** 与 **커넥티드（CONNECTED）** 共同签订。

第 1 条（目的）
本协议旨在规定双方在产品开发、设计及量产下单相关工作中，使用一方或客户提供的资料与信息时，应遵守的保密义务。

第 2 条（保密信息）
本协议所称保密信息，指平台（MASS CONNECTED 网站）内客户填写的资料、电子邮件资料、咨询过程中形成的图纸及会议内容、会议纪要等一切协商记录，以及客户的产品、商品化计划、价格政策、合同条件、营业方法、营销计划与策略、研发活动、生产计划、开发技术或计划、技术流程、设计、发明及研究计划、营业诀窍、商业秘密、客户信息等信息。

第 3 条（保密义务）
CONNECTED 未经提供保密信息的客户事先书面同意，不得将收到的保密信息用于本协议目的以外，亦不得向第三方提供、泄露或外流。

第 4 条（资料返还与销毁）
合同期结束后，若客户要求，CONNECTED 应立即将其持有的保密信息原件、复制件及试验件等，依提供方选择返还客户或销毁。电子信息保管 1 年后以不可恢复方式删除。

第 5 条（保密义务存续）
CONNECTED 所负义务在本协议终止或双方业务关系结束后仍存续 1 年。

第 6 条（损害赔偿等）
违反本协议规定并给对方造成损失的，违约方应赔偿对方损失。

第 7 条（知识产权）
提供给 CONNECTED 的一切信息均归客户所有。

第 8 条（合同期间）
本协议自签订日起 1 年有效。

第 9 条（一般事项）
本协议的解释与适用依大韩民国法律。与本协议相关的争议或问题，以客户所在地管辖地方法院为一审专属合意管辖法院。"""


class Command(BaseCommand):
    help = "Seed default NDA template (idempotent)."

    def handle(self, *args, **options):
        template, created = NdaTemplate.objects.update_or_create(
            version="2020-NDA-1",
            defaults={
                "title": "保密协议",
                "body": DEFAULT_NDA_BODY,
                "effective_date": timezone.now().date(),
                "is_active": True,
            },
        )
        NdaTemplate.objects.exclude(pk=template.pk).update(is_active=False)
        self.stdout.write(
            self.style.SUCCESS(f"NDA template {'created' if created else 'updated'}: {template.version}")
        )
