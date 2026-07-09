import type { DielineTemplateAsset } from './fefcoCatalog'
import type { DielineGeometry, DimField, LineKind, LineSegment } from './types'

type EntityRole = LineKind | 'dimension' | 'ignore'

export interface TransformedDimensionAnnotation {
  id: string
  field: DimField
  axis: 'horizontal' | 'vertical'
  x1: number
  y1: number
  x2: number
  y2: number
  labelX: number
  labelY: number
}

function roleToKind(role: string | undefined): LineKind | null {
  if (role === 'cut' || role === 'crease' || role === 'bleed') return role
  return null
}

function toNumber(value: unknown, fallback: number): number {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

function parametricTransform(asset: DielineTemplateAsset, geometry: DielineGeometry) {
  const parsed = asset.parsedGeometry || {}
  const mapping = asset.mappingSchema || {}
  const baseDimensions = mapping.base_dimensions || asset.baseDimensions || {}
  const bbox = parsed.bbox || { min_x: 0, min_y: 0, max_x: parsed.width || 1, max_y: parsed.height || 1 }
  const baseLength = toNumber(baseDimensions.length, parsed.width || bbox.max_x - bbox.min_x || 1)
  const baseHeight = toNumber(baseDimensions.height, parsed.height || bbox.max_y - bbox.min_y || 1)
  const scaleX = baseLength ? geometry.manufacturing.length / baseLength : 1
  const scaleY = baseHeight ? geometry.manufacturing.height / baseHeight : 1
  const originX = bbox.min_x || 0
  const originY = bbox.min_y || 0
  return {
    transformX: (value: unknown) => originX + (Number(value) - originX) * scaleX,
    transformY: (value: unknown) => originY + (Number(value) - originY) * scaleY,
  }
}

export function hasMappedParametricAsset(asset?: DielineTemplateAsset | null): asset is DielineTemplateAsset {
  return Boolean(
    asset &&
      asset.mappingStatus === 'mapped' &&
      asset.parsedGeometry?.entities?.length &&
      asset.mappingSchema?.entity_roles,
  )
}

export function buildParametricSegments(asset: DielineTemplateAsset, geometry: DielineGeometry): LineSegment[] {
  const parsed = asset.parsedGeometry || {}
  const mapping = asset.mappingSchema || {}
  const entityRoles = (mapping.entity_roles as Record<string, EntityRole>) || {}
  const { transformX, transformY } = parametricTransform(asset, geometry)

  return (parsed.entities || [])
    .map((entity) => {
      const kind = roleToKind(entityRoles[entity.entity_id] || entity.role)
      if (!kind) return null
      return {
        x1: transformX(entity.x1),
        y1: transformY(entity.y1),
        x2: transformX(entity.x2),
        y2: transformY(entity.y2),
        kind,
      }
    })
    .filter((item): item is LineSegment => Boolean(item))
}

export function buildParametricDimensionAnnotations(
  asset: DielineTemplateAsset,
  geometry: DielineGeometry,
): TransformedDimensionAnnotation[] {
  const annotations = asset.mappingSchema?.dimension_annotations || []
  if (!Array.isArray(annotations) || !annotations.length) return []
  const { transformX, transformY } = parametricTransform(asset, geometry)
  return annotations
    .map((ann) => {
      const field = ann.field
      if (field !== 'length' && field !== 'width' && field !== 'height') return null
      const x1 = transformX(ann.x1)
      const y1 = transformY(ann.y1)
      const x2 = transformX(ann.x2)
      const y2 = transformY(ann.y2)
      if (![x1, y1, x2, y2].every(Number.isFinite)) return null
      const axis = ann.axis || (Math.abs(x2 - x1) >= Math.abs(y2 - y1) ? 'horizontal' : 'vertical')
      return {
        id: ann.id || `dim_${field}`,
        field,
        axis,
        x1,
        y1,
        x2,
        y2,
        labelX: transformX(ann.label_x ?? (Number(ann.x1) + Number(ann.x2)) / 2),
        labelY: transformY(ann.label_y ?? (Number(ann.y1) + Number(ann.y2)) / 2),
      }
    })
    .filter((item): item is TransformedDimensionAnnotation => Boolean(item))
}

export function viewBoxFromSegments(segments: LineSegment[]): string {
  if (!segments.length) return '0 0 100 100'
  const xs = segments.flatMap((segment) => [segment.x1, segment.x2])
  const ys = segments.flatMap((segment) => [segment.y1, segment.y2])
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const width = Math.max(10, maxX - minX)
  const height = Math.max(10, maxY - minY)
  const pad = Math.max(20, Math.max(width, height) * 0.04)
  return `${minX - pad} ${minY - pad} ${width + pad * 2} ${height + pad * 2}`
}
