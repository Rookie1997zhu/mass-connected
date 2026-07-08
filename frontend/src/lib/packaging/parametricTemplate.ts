import type { DielineTemplateAsset } from './fefcoCatalog'
import type { DielineGeometry, LineKind, LineSegment } from './types'

type EntityRole = LineKind | 'dimension' | 'ignore'

function roleToKind(role: string | undefined): LineKind | null {
  if (role === 'cut' || role === 'crease' || role === 'bleed') return role
  return null
}

function toNumber(value: unknown, fallback: number): number {
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
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
  const baseDimensions = (mapping.base_dimensions as Record<string, unknown>) || asset.baseDimensions || {}
  const bbox = parsed.bbox || { min_x: 0, min_y: 0, max_x: parsed.width || 1, max_y: parsed.height || 1 }
  const baseLength = toNumber(baseDimensions.length, parsed.width || bbox.max_x - bbox.min_x || 1)
  const baseHeight = toNumber(baseDimensions.height, parsed.height || bbox.max_y - bbox.min_y || 1)
  const scaleX = baseLength ? geometry.manufacturing.length / baseLength : 1
  const scaleY = baseHeight ? geometry.manufacturing.height / baseHeight : 1
  const originX = bbox.min_x || 0
  const originY = bbox.min_y || 0
  const entityRoles = (mapping.entity_roles as Record<string, EntityRole>) || {}

  return (parsed.entities || [])
    .map((entity) => {
      const kind = roleToKind(entityRoles[entity.entity_id] || entity.role)
      if (!kind) return null
      return {
        x1: originX + (Number(entity.x1) - originX) * scaleX,
        y1: originY + (Number(entity.y1) - originY) * scaleY,
        x2: originX + (Number(entity.x2) - originX) * scaleX,
        y2: originY + (Number(entity.y2) - originY) * scaleY,
        kind,
      }
    })
    .filter((item): item is LineSegment => Boolean(item))
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
