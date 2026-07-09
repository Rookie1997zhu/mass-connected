export type FefcoPriority = 'P0' | 'P1'
export type EngineKey = 'slotted_rsc' | 'folding_shipping' | 'mailer_folder' | 'tuck_end' | 'auto_lock_bottom'
export type DimensionType = 'internal' | 'external' | 'manufacturing'
export type FluteType = 'e' | 'b' | 'c' | 'bc' | 'none'
export type MaterialType = 'corrugated' | 'white_card' | 'kraft' | 'coated'

export interface SizeTripleMm {
  lengthMm?: number
  widthMm?: number
  heightMm?: number
}

export interface FefcoCategory {
  id?: number
  code: string
  nameKey: string
  descKey: string
  nameI18n?: Record<string, string>
  descI18n?: Record<string, string>
  sortOrder: number
  isActive?: boolean
}

export interface FefcoBoxTemplate {
  id?: number
  code: string
  categoryCode: string
  nameKey: string
  descKey: string
  nameI18n?: Record<string, string>
  descI18n?: Record<string, string>
  engineKey: EngineKey
  algorithmKey: EngineKey
  priority: FefcoPriority
  quoteEnabled: boolean
  previewEnabled: boolean
  inputs: string[]
  sortOrder: number
  defaultLengthMm?: number
  defaultWidthMm?: number
  defaultHeightMm?: number
  defaultManufacturingLengthMm?: number
  defaultManufacturingWidthMm?: number
  defaultManufacturingHeightMm?: number
  defaultInternalLengthMm?: number
  defaultInternalWidthMm?: number
  defaultInternalHeightMm?: number
  defaultExternalLengthMm?: number
  defaultExternalWidthMm?: number
  defaultExternalHeightMm?: number
  defaultThicknessMm?: number
  defaultGlueTabMm?: number
  fluteType?: FluteType
  materialType?: MaterialType
  defaultDimensionType?: DimensionType
  minLengthMm?: number | null
  maxLengthMm?: number | null
  minWidthMm?: number | null
  maxWidthMm?: number | null
  minHeightMm?: number | null
  maxHeightMm?: number | null
  slotGapMm?: number | null
  creaseGapMm?: number | null
  flapGapMm?: number | null
  structureParams?: Record<string, unknown>
  allowances?: Record<string, number>
  productionAssetUrl?: string | null
  parametricAssetStatus?: string
  activeParametricAsset?: DielineTemplateAsset | null
  thumbnailUrl?: string | null
}

export interface ParsedDielineEntity {
  entity_id: string
  type: string
  role?: string
  x1: number
  y1: number
  x2: number
  y2: number
  layer?: string
  color?: string
  linetype?: string
}

export interface ParsedDielineGeometry {
  schema_version?: number
  source_format?: string
  unit?: string
  bbox?: { min_x: number; min_y: number; max_x: number; max_y: number }
  width?: number
  height?: number
  entities?: ParsedDielineEntity[]
}

export type DielineDimensionField = 'length' | 'width' | 'height'
export type DielineDimensionAxis = 'horizontal' | 'vertical'
export type DielineDimensionSource = 'entity' | 'manual'

export interface DielineDimensionAnnotation {
  id: string
  field: DielineDimensionField
  axis?: DielineDimensionAxis
  source?: DielineDimensionSource
  entity_id?: string | null
  x1: number
  y1: number
  x2: number
  y2: number
  label_x?: number
  label_y?: number
}

export interface DielineMappingSchema {
  schema_version?: number
  mapping_mode?: string
  base_dimensions?: Record<string, unknown>
  dimension_refs?: Record<string, unknown>
  dimension_annotations?: DielineDimensionAnnotation[]
  entity_roles?: Record<string, unknown>
  transform_rules?: Record<string, unknown>
}

export interface DielineTemplateAsset {
  id: number
  sourceFormat?: string
  sourceFileUrl?: string | null
  parsedGeometry: ParsedDielineGeometry
  mappingSchema: DielineMappingSchema
  baseDimensions: Record<string, unknown>
  version?: number
  mappingStatus?: string
}

let runtimeTemplates: FefcoBoxTemplate[] = []
let runtimeCategories: FefcoCategory[] = []

function toNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === '') return undefined
  const n = Number(value)
  return Number.isFinite(n) ? n : undefined
}

export function normalizeCatalogTemplate(raw: Record<string, unknown>): FefcoBoxTemplate {
  const code = String(raw.code || '')
  const engineKey = String(raw.engine_key || raw.algorithm_key || 'slotted_rsc') as EngineKey
  const mfgL = toNumber(raw.default_manufacturing_length_mm) ?? toNumber(raw.default_length_mm)
  const mfgW = toNumber(raw.default_manufacturing_width_mm) ?? toNumber(raw.default_width_mm)
  const mfgH = toNumber(raw.default_manufacturing_height_mm) ?? toNumber(raw.default_height_mm)
  return {
    id: raw.id != null ? Number(raw.id) : undefined,
    code,
    categoryCode: String(raw.category_code || ''),
    nameKey: String(raw.name_key || `fefcoBox${code}`),
    descKey: String(raw.desc_key || `fefcoBox${code}Desc`),
    nameI18n: (raw.name_i18n as Record<string, string>) || {},
    descI18n: (raw.desc_i18n as Record<string, string>) || {},
    engineKey,
    algorithmKey: engineKey,
    priority: (raw.priority as FefcoPriority) || 'P0',
    quoteEnabled: Boolean(raw.quote_enabled),
    previewEnabled: Boolean(raw.preview_enabled),
    inputs: Array.isArray(raw.inputs) ? (raw.inputs as string[]) : ['length_mm', 'width_mm', 'height_mm', 'thickness_mm'],
    sortOrder: Number(raw.sort_order) || 0,
    defaultLengthMm: mfgL,
    defaultWidthMm: mfgW,
    defaultHeightMm: mfgH,
    defaultManufacturingLengthMm: mfgL,
    defaultManufacturingWidthMm: mfgW,
    defaultManufacturingHeightMm: mfgH,
    defaultInternalLengthMm: toNumber(raw.default_internal_length_mm),
    defaultInternalWidthMm: toNumber(raw.default_internal_width_mm),
    defaultInternalHeightMm: toNumber(raw.default_internal_height_mm),
    defaultExternalLengthMm: toNumber(raw.default_external_length_mm),
    defaultExternalWidthMm: toNumber(raw.default_external_width_mm),
    defaultExternalHeightMm: toNumber(raw.default_external_height_mm),
    defaultThicknessMm: toNumber(raw.default_thickness_mm),
    defaultGlueTabMm: toNumber(raw.default_glue_tab_mm),
    fluteType: (raw.flute_type as FluteType) || undefined,
    materialType: (raw.material_type as MaterialType) || undefined,
    defaultDimensionType: (raw.default_dimension_type as DimensionType) || 'internal',
    minLengthMm: toNumber(raw.min_length_mm) ?? null,
    maxLengthMm: toNumber(raw.max_length_mm) ?? null,
    minWidthMm: toNumber(raw.min_width_mm) ?? null,
    maxWidthMm: toNumber(raw.max_width_mm) ?? null,
    minHeightMm: toNumber(raw.min_height_mm) ?? null,
    maxHeightMm: toNumber(raw.max_height_mm) ?? null,
    slotGapMm: toNumber(raw.slot_gap_mm) ?? null,
    creaseGapMm: toNumber(raw.crease_gap_mm) ?? null,
    flapGapMm: toNumber(raw.flap_gap_mm) ?? null,
    structureParams: (raw.structure_params as Record<string, unknown>) || {},
    allowances: (raw.allowances as Record<string, number>) || {},
    productionAssetUrl: (raw.production_asset_url as string) || null,
    parametricAssetStatus: String(raw.parametric_asset_status || 'none'),
    activeParametricAsset: normalizeTemplateAsset(raw.active_parametric_asset as Record<string, unknown> | null),
    thumbnailUrl: (raw.thumbnail_url as string) || null,
  }
}

function normalizeTemplateAsset(raw?: Record<string, unknown> | null): DielineTemplateAsset | null {
  if (!raw) return null
  return {
    id: Number(raw.id),
    sourceFormat: String(raw.source_format || ''),
    sourceFileUrl: (raw.source_file_url as string) || null,
    parsedGeometry: (raw.parsed_geometry as ParsedDielineGeometry) || {},
    mappingSchema: (raw.mapping_schema as DielineMappingSchema) || {},
    baseDimensions: (raw.base_dimensions as Record<string, unknown>) || {},
    version: toNumber(raw.version),
    mappingStatus: String(raw.mapping_status || ''),
  }
}

export function normalizeCatalogCategory(raw: Record<string, unknown>): FefcoCategory {
  const code = String(raw.code || '')
  return {
    id: raw.id != null ? Number(raw.id) : undefined,
    code,
    nameKey: String(raw.name_key || `fefcoCat${code}`),
    descKey: String(raw.desc_key || `fefcoCat${code}Desc`),
    nameI18n: (raw.name_i18n as Record<string, string>) || {},
    descI18n: (raw.desc_i18n as Record<string, string>) || {},
    sortOrder: Number(raw.sort_order) || 0,
    isActive: raw.is_active !== false,
  }
}

export function setFefcoCatalogFromApi(payload: {
  categories?: Record<string, unknown>[]
  templates?: Record<string, unknown>[]
}) {
  runtimeCategories = Array.isArray(payload.categories)
    ? payload.categories.map(normalizeCatalogCategory)
    : []
  runtimeTemplates = Array.isArray(payload.templates)
    ? payload.templates.map(normalizeCatalogTemplate)
    : []
}

export function resetFefcoCatalog() {
  runtimeCategories = []
  runtimeTemplates = []
}

const templateMap = () => new Map(runtimeTemplates.map((item) => [item.code, item]))

export function getBoxTemplate(code: string): FefcoBoxTemplate | undefined {
  return templateMap().get(code)
}

export function getEngineKey(code: string): EngineKey | undefined {
  return getBoxTemplate(code)?.engineKey
}

export function templatesByCategory(categoryCode: string): FefcoBoxTemplate[] {
  return runtimeTemplates.filter((item) => item.categoryCode === categoryCode)
}

export function categoriesWithTemplates(): Array<FefcoCategory & { templates: FefcoBoxTemplate[] }> {
  return runtimeCategories
    .map((cat) => ({
      ...cat,
      templates: templatesByCategory(cat.code),
    }))
    .filter((cat) => cat.templates.length > 0)
}

export function defaultDimsForTemplate(
  template: FefcoBoxTemplate | undefined,
  dimensionType: DimensionType,
): SizeTripleMm | null {
  if (!template) return null
  if (dimensionType === 'internal') {
    return {
      lengthMm: template.defaultInternalLengthMm,
      widthMm: template.defaultInternalWidthMm,
      heightMm: template.defaultInternalHeightMm,
    }
  }
  if (dimensionType === 'external') {
    return {
      lengthMm: template.defaultExternalLengthMm,
      widthMm: template.defaultExternalWidthMm,
      heightMm: template.defaultExternalHeightMm,
    }
  }
  return {
    lengthMm: template.defaultManufacturingLengthMm ?? template.defaultLengthMm,
    widthMm: template.defaultManufacturingWidthMm ?? template.defaultWidthMm,
    heightMm: template.defaultManufacturingHeightMm ?? template.defaultHeightMm,
  }
}

export type BoxCode = string

export const QUOTE_ENABLED_CODES = () =>
  runtimeTemplates.filter((t) => t.quoteEnabled).map((t) => t.code)

export const hasCatalogData = () => runtimeCategories.length > 0 || runtimeTemplates.length > 0
