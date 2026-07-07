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
  { code: '0200', nameKey: 'fefcoCat0200', descKey: 'fefcoCat0200Desc', sortOrder: 20 },
  { code: '0400', nameKey: 'fefcoCat0400', descKey: 'fefcoCat0400Desc', sortOrder: 40 },
  { code: '0700', nameKey: 'fefcoCat0700', descKey: 'fefcoCat0700Desc', sortOrder: 70 },
]

export const FEFCO_BOX_TEMPLATES: FefcoBoxTemplate[] = [
  { code: '0201', categoryCode: '0200', nameKey: 'fefcoBox0201', descKey: 'fefcoBox0201Desc', algorithmKey: 'slotted_rsc', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 1 },
  { code: '0427', categoryCode: '0400', nameKey: 'fefcoBox0427', descKey: 'fefcoBox0427Desc', algorithmKey: 'mailer_folder', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 2 },
  { code: '0713', categoryCode: '0700', nameKey: 'fefcoBox0713', descKey: 'fefcoBox0713Desc', algorithmKey: 'tuck_end', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 3 },
  { code: '0716', categoryCode: '0700', nameKey: 'fefcoBox0716', descKey: 'fefcoBox0716Desc', algorithmKey: 'auto_lock_bottom', priority: 'P0', quoteEnabled: true, previewEnabled: true, inputs: ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'], sortOrder: 4 },
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
