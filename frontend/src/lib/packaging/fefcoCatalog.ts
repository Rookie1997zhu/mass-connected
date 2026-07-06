export type FefcoPriority = 'P0' | 'P1'

export interface FefcoCategory {
  code: string
  nameKey: string
  descKey: string
  sortOrder: number
}

export interface FefcoBoxTemplate {
  code: string
  categoryCode: string
  nameKey: string
  descKey: string
  algorithmKey: string
  priority: FefcoPriority
  quoteEnabled: boolean
  previewEnabled: boolean
  inputs: string[]
  sortOrder: number
}

export const FEFCO_CATEGORIES: FefcoCategory[] = [
  { code: '0100', nameKey: 'fefcoCat0100', descKey: 'fefcoCat0100Desc', sortOrder: 10 },
  { code: '0200', nameKey: 'fefcoCat0200', descKey: 'fefcoCat0200Desc', sortOrder: 20 },
  { code: '0300', nameKey: 'fefcoCat0300', descKey: 'fefcoCat0300Desc', sortOrder: 30 },
  { code: '0400', nameKey: 'fefcoCat0400', descKey: 'fefcoCat0400Desc', sortOrder: 40 },
  { code: '0500', nameKey: 'fefcoCat0500', descKey: 'fefcoCat0500Desc', sortOrder: 50 },
  { code: '0600', nameKey: 'fefcoCat0600', descKey: 'fefcoCat0600Desc', sortOrder: 60 },
  { code: '0700', nameKey: 'fefcoCat0700', descKey: 'fefcoCat0700Desc', sortOrder: 70 },
  { code: '0800', nameKey: 'fefcoCat0800', descKey: 'fefcoCat0800Desc', sortOrder: 80 },
  { code: '0900', nameKey: 'fefcoCat0900', descKey: 'fefcoCat0900Desc', sortOrder: 90 },
]

export const FEFCO_BOX_TEMPLATES: FefcoBoxTemplate[] = [
  { code: '0201', categoryCode: '0200', nameKey: 'fefcoBox0201', descKey: 'fefcoBox0201Desc', algorithmKey: 'slotted_rsc', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 1 },
  { code: '0427', categoryCode: '0400', nameKey: 'fefcoBox0427', descKey: 'fefcoBox0427Desc', algorithmKey: 'mailer_folder', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 2 },
  { code: '0713', categoryCode: '0700', nameKey: 'fefcoBox0713', descKey: 'fefcoBox0713Desc', algorithmKey: 'tuck_end', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 3 },
  { code: '0716', categoryCode: '0700', nameKey: 'fefcoBox0716', descKey: 'fefcoBox0716Desc', algorithmKey: 'auto_lock_bottom', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 4 },
  { code: '0301', categoryCode: '0300', nameKey: 'fefcoBox0301', descKey: 'fefcoBox0301Desc', algorithmKey: 'telescope', priority: 'P1', quoteEnabled: false, previewEnabled: false, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 5 },
  { code: '0501', categoryCode: '0500', nameKey: 'fefcoBox0501', descKey: 'fefcoBox0501Desc', algorithmKey: 'slide_sleeve', priority: 'P1', quoteEnabled: false, previewEnabled: false, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 6 },
  { code: '0502', categoryCode: '0500', nameKey: 'fefcoBox0502', descKey: 'fefcoBox0502Desc', algorithmKey: 'slide_drawer', priority: 'P1', quoteEnabled: false, previewEnabled: false, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 7 },
  { code: '0904', categoryCode: '0900', nameKey: 'fefcoBox0904', descKey: 'fefcoBox0904Desc', algorithmKey: 'cross_partition', priority: 'P1', quoteEnabled: false, previewEnabled: false, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 8 },
]

const templateMap = new Map(FEFCO_BOX_TEMPLATES.map((item) => [item.code, item]))

export function getBoxTemplate(code: string): FefcoBoxTemplate | undefined {
  return templateMap.get(code)
}

export function templatesByCategory(categoryCode: string): FefcoBoxTemplate[] {
  return FEFCO_BOX_TEMPLATES.filter((item) => item.categoryCode === categoryCode)
}

export function categoriesWithTemplates(): Array<FefcoCategory & { templates: FefcoBoxTemplate[] }> {
  return FEFCO_CATEGORIES.map((cat) => ({
    ...cat,
    templates: templatesByCategory(cat.code),
  })).filter((cat) => cat.templates.length > 0)
}

export type BoxCode = (typeof FEFCO_BOX_TEMPLATES)[number]['code']

export const QUOTE_ENABLED_CODES = FEFCO_BOX_TEMPLATES.filter((t) => t.quoteEnabled).map((t) => t.code)
