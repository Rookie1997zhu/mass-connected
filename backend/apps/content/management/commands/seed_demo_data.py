from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Category, Product
from apps.content.models import Case, ContentPage, FAQ, NavItem, News
from apps.rfq.models import ServiceCategory
from apps.simplequote.calculator import DEFAULT_PARAMS

INJECTION_PARAM_META = {
    "mold_base_ABS": ("基本模具费 ABS 普通", "RMB"),
    "mold_base_ABS_Gf": ("基本模具费 ABS+Gf", "RMB"),
    "mold_base_PC": ("基本模具费 PC", "RMB"),
    "mold_base_PA66": ("基本模具费 PA66", "RMB"),
    "mold_base_PP": ("基本模具费 PP", "RMB"),
    "unit_price_kg_ABS": ("基本单价 ABS 普通", "RMB/kg"),
    "unit_price_kg_ABS_Gf": ("基本单价 ABS+Gf", "RMB/kg"),
    "unit_price_kg_PC": ("基本单价 PC", "RMB/kg"),
    "unit_price_kg_PA66": ("基本单价 PA66", "RMB/kg"),
    "unit_price_kg_PP": ("基本单价 PP", "RMB/kg"),
    "unit_base_ABS": ("基本报价(1g以下) ABS 普通", "RMB"),
    "unit_base_ABS_Gf": ("基本报价(1g以下) ABS+Gf", "RMB"),
    "unit_base_PC": ("基本报价(1g以下) PC", "RMB"),
    "unit_base_PA66": ("基本报价(1g以下) PA66", "RMB"),
    "unit_base_PP": ("基本报价(1g以下) PP", "RMB"),
    "slider_unit": ("滑块每个加价", "RMB"),
    "precision_add": ("精密度 ≤0.2mm 加价", "RMB"),
    "loss_factor": ("耗材重量损耗系数", "x"),
    "color_transparent": ("透明加重比例", "rate"),
    "color_semi": ("半透明加重比例", "rate"),
    "packaging_rate": ("包装费比例", "rate"),
    "profit_rate": ("利润率", "rate"),
    "rmb_to_krw": ("RMB→KRW 展示汇率", "KRW/RMB"),
    "moq_kg": ("未指定 PANTONE 时 MOQ", "KG"),
    "density_ABS": ("材料密度 ABS 普通", "g/cm³"),
    "density_ABS_Gf": ("材料密度 ABS+Gf", "g/cm³"),
    "density_PC": ("材料密度 PC", "g/cm³"),
    "density_PA66": ("材料密度 PA66", "g/cm³"),
    "density_PP": ("材料密度 PP", "g/cm³"),
}

SERVICE_CATEGORIES = [
    {
        "slug": "cnc-machining",
        "sort_order": 1,
        "icon": "cnc",
        "name": {"ko": "CNC 가공", "zh": "CNC 加工", "en": "CNC Machining", "ja": "CNC加工"},
    },
    {
        "slug": "sheet-metal",
        "sort_order": 2,
        "icon": "sheet",
        "name": {"ko": "판금 가공", "zh": "钣金加工", "en": "Sheet Metal", "ja": "板金加工"},
    },
    {
        "slug": "injection-molding",
        "sort_order": 3,
        "icon": "injection",
        "name": {"ko": "사출 성형", "zh": "注塑成型", "en": "Injection Molding", "ja": "射出成形"},
    },
    {
        "slug": "die-casting",
        "sort_order": 4,
        "icon": "casting",
        "name": {"ko": "다이캐스팅", "zh": "压铸", "en": "Die Casting", "ja": "ダイカスト"},
    },
    {
        "slug": "surface-treatment",
        "sort_order": 5,
        "icon": "surface",
        "name": {"ko": "표면 처리", "zh": "表面处理", "en": "Surface Treatment", "ja": "表面処理"},
    },
    {
        "slug": "3d-printing",
        "sort_order": 6,
        "icon": "3dp",
        "name": {"ko": "3D 프린팅", "zh": "3D 打印", "en": "3D Printing", "ja": "3Dプリント"},
    },
]

PRODUCT_CATEGORIES = [
    {
        "slug": "standard-parts",
        "sort_order": 1,
        "name": {"ko": "표준 부품", "zh": "标准件", "en": "Standard Parts", "ja": "標準部品"},
    },
    {
        "slug": "custom-components",
        "sort_order": 2,
        "name": {"ko": "맞춤 부품", "zh": "定制件", "en": "Custom Components", "ja": "カスタム部品"},
    },
]

DEMO_PRODUCTS = [
    {
        "sku": "DEMO-001",
        "category_slug": "standard-parts",
        "name": {"ko": "데모 CNC 부품", "zh": "演示 CNC 零件", "en": "Demo CNC Part", "ja": "デモCNC部品"},
        "description": {"ko": "자사 표준 CNC 부품", "zh": "本公司标准 CNC 零件", "en": "Standard CNC part", "ja": "自社標準CNC部品"},
        "price_amount": 50000,
        "stock": 100,
    },
    {
        "sku": "DEMO-002",
        "category_slug": "custom-components",
        "name": {"ko": "데모 판금 부품", "zh": "演示钣金件", "en": "Demo Sheet Metal Part", "ja": "デモ板金部品"},
        "description": {"ko": "맞춤 판금 가공 부품", "zh": "定制钣金加工件", "en": "Custom sheet metal part", "ja": "カスタム板金部品"},
        "price_amount": 80000,
        "stock": 50,
    },
]


NAV_MENU = [
    {
        "sort_order": 1,
        "label": {"ko": "제조 견적", "zh": "制造报价", "en": "Manufacturing Quote", "ja": "製造見積"},
        "children": [
            {
                "path": "/rfq/new",
                "sort_order": 1,
                "label": {"ko": "요청 등록", "zh": "发布请求", "en": "Post Request", "ja": "依頼投稿"},
            },
            {
                "path": "/demand-hall",
                "sort_order": 2,
                "label": {"ko": "수요 찾기", "zh": "寻找需求", "en": "Find Demands", "ja": "需要検索"},
            },
            {
                "path": "/partners",
                "sort_order": 3,
                "label": {"ko": "파트너", "zh": "合作伙伴", "en": "Partners", "ja": "パートナー"},
            },
        ],
    },
    {
        "sort_order": 2,
        "label": {"ko": "쇼핑몰", "zh": "商城", "en": "Shop", "ja": "ショップ"},
        "children": [
            {
                "path": "/shop",
                "sort_order": 1,
                "label": {"ko": "상품 분류", "zh": "产品分类", "en": "Categories", "ja": "商品カテゴリ"},
            },
        ],
    },
    {
        "sort_order": 3,
        "label": {"ko": "소개", "zh": "关于", "en": "About", "ja": "会社情報"},
        "children": [
            {
                "path": "/capabilities",
                "sort_order": 1,
                "label": {"ko": "제조 역량", "zh": "制造能力", "en": "Capabilities", "ja": "製造能力"},
            },
            {
                "path": "/oem-odm",
                "sort_order": 2,
                "label": {"ko": "OEM/ODM", "zh": "OEM/ODM", "en": "OEM/ODM", "ja": "OEM/ODM"},
            },
            {
                "path": "/cases",
                "sort_order": 3,
                "label": {"ko": "사례", "zh": "案例", "en": "Cases", "ja": "事例"},
            },
            {
                "path": "/news",
                "sort_order": 4,
                "label": {"ko": "뉴스", "zh": "资讯", "en": "News", "ja": "ニュース"},
            },
            {
                "path": "/support/faq",
                "sort_order": 5,
                "label": {"ko": "지원", "zh": "支持", "en": "Support", "ja": "サポート"},
            },
            {
                "path": "/contact",
                "sort_order": 6,
                "label": {"ko": "문의", "zh": "联系", "en": "Contact", "ja": "お問い合わせ"},
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed demo service categories, shop catalog and content data"

    def handle(self, *args, **options):
        from apps.simplequote.models import QuoteParam

        for key, value in DEFAULT_PARAMS.get("injection", {}).items():
            label, unit = INJECTION_PARAM_META.get(key, ("", ""))
            QuoteParam.objects.get_or_create(
                quote_type="injection",
                param_key=key,
                defaults={"value": value, "label": label, "unit": unit, "is_active": True},
            )
        for item in SERVICE_CATEGORIES:
            ServiceCategory.objects.get_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "icon": item["icon"],
                    "sort_order": item["sort_order"],
                    "is_active": True,
                },
            )
        for item in PRODUCT_CATEGORIES:
            Category.objects.get_or_create(
                slug=item["slug"],
                defaults={
                    "name": item["name"],
                    "sort_order": item["sort_order"],
                    "is_active": True,
                },
            )
        for item in DEMO_PRODUCTS:
            category = Category.objects.filter(slug=item["category_slug"]).first()
            if category:
                Product.objects.get_or_create(
                    sku=item["sku"],
                    defaults={
                        "category": category,
                        "name": item["name"],
                        "description": item["description"],
                        "price_amount": item["price_amount"],
                        "stock": item["stock"],
                        "is_active": True,
                        "is_shop_visible": True,
                    },
                )
        ContentPage.objects.get_or_create(
            page_key="about.profile",
            defaults={
                "title": {"ko": "회사 소개", "en": "Company Profile"},
                "body": {"ko": "OEM / ODM 전문 제조사", "en": "Professional OEM / ODM manufacturer"},
            },
        )
        if not Case.objects.filter(title__ko="데모 케이스").exists():
            Case.objects.create(
                title={"ko": "데모 케이스", "en": "Demo Case"},
                summary={"ko": "OEM 제조 사례", "en": "OEM manufacturing case"},
                content={"ko": "성공적인 OEM 협력 사례입니다.", "en": "Successful OEM partnership."},
                is_published=True,
                published_at=timezone.now(),
            )
        if not News.objects.filter(title__ko="데모 뉴스").exists():
            News.objects.create(
                title={"ko": "데모 뉴스", "en": "Demo News"},
                summary={"ko": "회사 소식", "en": "Company news"},
                content={"ko": "OEM 플랫폼 런칭", "en": "OEM platform launch"},
                is_published=True,
                published_at=timezone.now(),
            )
        if not FAQ.objects.filter(question__ko="MOQ는 어떻게 되나요?").exists():
            FAQ.objects.create(
                question={"ko": "MOQ는 어떻게 되나요?", "en": "What is the MOQ?"},
                answer={"ko": "제품별 MOQ는 문의해 주세요.", "en": "MOQ varies by product."},
                sort_order=1,
                is_active=True,
            )
        if not NavItem.objects.exists():
            for group in NAV_MENU:
                parent = NavItem.objects.create(
                    label=group["label"],
                    sort_order=group["sort_order"],
                    is_active=True,
                )
                for child in group["children"]:
                    NavItem.objects.create(
                        parent=parent,
                        path=child["path"],
                        label=child["label"],
                        sort_order=child["sort_order"],
                        is_active=True,
                    )
        self.stdout.write(self.style.SUCCESS("Seed data ready"))
