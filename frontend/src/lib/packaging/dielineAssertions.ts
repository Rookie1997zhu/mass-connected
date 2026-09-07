import {
  build0201Segments,
  buildPreview,
  computeDimViewBox,
  computeGeometry,
  exportDxf,
  getDimAnnotations,
} from './boxEngine'
import { viewBoxFromSegments } from './parametricTemplate'
import { buildDielinePdfBytes } from './dielineExport'
import { build0427Segments, compute0427BlankSize } from './dieline0427'
import { buildTuckEndSegments } from './dieline0713'
import { buildAutoLockBottomSegments } from './dieline0716'
import { buildFoldingShippingSegments } from './dielineFoldingShipping'
import { REFERENCE_0201 } from './boxPresets'
import { getBoxTemplate, setFefcoCatalogFromApi } from './fefcoCatalog'
import type { BoxParams, LineSegment } from './types'

function seedTestCatalog() {
  setFefcoCatalogFromApi({
    categories: [
      { code: '0200', name_i18n: { zh: '开槽箱' }, sort_order: 20 },
      { code: '0400', name_i18n: { zh: '翻盖箱' }, sort_order: 40 },
      { code: '0700', name_i18n: { zh: '插舌盒' }, sort_order: 70 },
    ],
    templates: [
      {
        code: '0201',
        category_code: '0200',
        engine_key: 'slotted_rsc',
        geometry_mode: 'formula',
        purchase_enabled: true,
        quote_enabled: true,
        preview_enabled: true,
        sort_order: 1,
        default_manufacturing_length_mm: 434,
        default_manufacturing_width_mm: 214,
        default_manufacturing_height_mm: 278,
        default_internal_length_mm: 430,
        default_internal_width_mm: 210,
        default_internal_height_mm: 270,
        default_external_length_mm: 436,
        default_external_width_mm: 216,
        default_external_height_mm: 282,
        default_thickness_mm: 3,
        min_length_mm: null,
        max_length_mm: null,
      },
      {
        code: '0210',
        category_code: '0200',
        engine_key: 'folding_shipping',
        quote_enabled: true,
        preview_enabled: true,
        sort_order: 2,
        default_manufacturing_length_mm: 354,
        default_manufacturing_width_mm: 354,
        default_manufacturing_height_mm: 208,
        default_internal_length_mm: 350,
        default_internal_width_mm: 350,
        default_internal_height_mm: 200,
        default_external_length_mm: 356,
        default_external_width_mm: 356,
        default_external_height_mm: 216,
        default_thickness_mm: 3,
      },
      {
        code: '0427',
        category_code: '0400',
        engine_key: 'mailer_folder',
        quote_enabled: true,
        preview_enabled: true,
        sort_order: 3,
        default_manufacturing_length_mm: 315,
        default_manufacturing_width_mm: 202,
        default_manufacturing_height_mm: 62,
        default_thickness_mm: 1.5,
        material_type: 'white_card',
        flute_type: 'none',
      },
      {
        code: '0713',
        category_code: '0700',
        engine_key: 'tuck_end',
        quote_enabled: true,
        preview_enabled: true,
        sort_order: 4,
        default_manufacturing_length_mm: 200,
        default_manufacturing_width_mm: 150,
        default_manufacturing_height_mm: 100,
        default_thickness_mm: 1.5,
        material_type: 'white_card',
        flute_type: 'none',
        flap_gap_mm: 2,
      },
      {
        code: '0716',
        category_code: '0700',
        engine_key: 'auto_lock_bottom',
        quote_enabled: true,
        preview_enabled: true,
        sort_order: 5,
        default_manufacturing_length_mm: 200,
        default_manufacturing_width_mm: 150,
        default_manufacturing_height_mm: 100,
        default_thickness_mm: 1.5,
        material_type: 'white_card',
        flute_type: 'none',
        flap_gap_mm: 2,
      },
      {
        code: '9998',
        category_code: '0200',
        engine_key: 'slotted_rsc',
        geometry_mode: 'fixed_asset',
        purchase_enabled: true,
        quote_enabled: true,
        preview_enabled: true,
        sort_order: 99,
        default_manufacturing_length_mm: 100,
        default_manufacturing_width_mm: 80,
        default_manufacturing_height_mm: 50,
        default_thickness_mm: 1.5,
        parametric_asset_status: 'mapped',
        active_parametric_asset: {
          id: 1,
          source_format: 'svg',
          version: 1,
          mapping_status: 'mapped',
          base_dimensions: { length: 100, width: 80, height: 50, thickness: 1.5 },
          mapping_schema: {
            schema_version: 1,
            mapping_mode: 'orthogonal_scale',
            base_dimensions: { length: 100, width: 80, height: 50, thickness: 1.5 },
            entity_roles: { svg_00001: 'cut', svg_00002: 'crease', svg_00003: 'ignore' },
            dimension_annotations: [
              {
                id: 'dim_length_001',
                field: 'length',
                axis: 'horizontal',
                source: 'entity',
                entity_id: 'svg_00001',
                x1: 0,
                y1: 0,
                x2: 100,
                y2: 0,
                label_x: 50,
                label_y: -10,
              },
              {
                id: 'dim_width_001',
                field: 'width',
                axis: 'horizontal',
                source: 'manual',
                x1: 0,
                y1: 25,
                x2: 80,
                y2: 25,
                label_x: 40,
                label_y: 15,
              },
              {
                id: 'dim_height_001',
                field: 'height',
                axis: 'vertical',
                source: 'entity',
                entity_id: 'svg_00002',
                x1: 100,
                y1: 0,
                x2: 100,
                y2: 50,
                label_x: 112,
                label_y: 25,
              },
            ],
            transform_rules: { x: 'length', y: 'height' },
          },
          parsed_geometry: {
            schema_version: 1,
            source_format: 'svg',
            unit: 'mm',
            bbox: { min_x: 0, min_y: 0, max_x: 100, max_y: 50 },
            width: 100,
            height: 50,
            entities: [
              { entity_id: 'svg_00001', type: 'line', role: 'cut', x1: 0, y1: 0, x2: 100, y2: 0 },
              { entity_id: 'svg_00002', type: 'line', role: 'crease', x1: 100, y1: 0, x2: 100, y2: 50 },
              { entity_id: 'svg_00003', type: 'line', role: 'ignore', x1: 0, y1: 50, x2: 100, y2: 50 },
            ],
          },
        },
      },
    ],
  })
}

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`)
  }
}

function horizontalCutsAt(segments: LineSegment[], y: number, tolerance = 0.01): LineSegment[] {
  return segments.filter(
    (seg) =>
      seg.kind === 'cut' &&
      Math.abs(seg.y1 - y) < tolerance &&
      Math.abs(seg.y2 - y) < tolerance &&
      Math.abs(seg.x1 - seg.x2) > tolerance,
  )
}

function verticalCutsAt(segments: LineSegment[], x: number, tolerance = 0.01): LineSegment[] {
  return segments.filter(
    (seg) =>
      seg.kind === 'cut' &&
      Math.abs(seg.x1 - x) < tolerance &&
      Math.abs(seg.x2 - x) < tolerance &&
      Math.abs(seg.y1 - seg.y2) > tolerance,
  )
}

function countByKind(segments: LineSegment[], kind: LineSegment['kind']): number {
  return segments.filter((seg) => seg.kind === kind).length
}

function to0201Params(): BoxParams {
  const preset = REFERENCE_0201
  return {
    boxCode: '0201',
    length: preset.length,
    width: preset.width,
    height: preset.height,
    thickness: preset.thickness,
    unit: preset.unit,
    dimensionType: preset.dimensionType,
    boardType: preset.boardType,
    quantity: 1,
    printColors: 0,
  }
}

export function runDielineAssertions(): void {
  seedTestCatalog()
  const params = to0201Params()
  const geometry = computeGeometry(params)
  const segments = build0201Segments(geometry)
  const preview = {
    geometry,
    segments,
    viewBox: viewBoxFromSegments(segments),
    previewMode: 'detailed' as const,
    source: 'engine' as const,
  }

  const L = geometry.manufacturing.length
  const W = geometry.manufacturing.width
  const glue = geometry.glueTabMm
  const xW1 = glue + L
  const xL2 = glue + L + W
  const xW2 = glue + L + W + L
  const slotW = geometry.thicknessMm
  const half = slotW / 2

  assert(geometry.blankWidthMm === 2 * (L + W) + glue, '0201 blank width unchanged')
  assert(geometry.blankHeightMm === W + geometry.manufacturing.height, '0201 blank height unchanged')

  const cutCount = countByKind(segments, 'cut')
  const creaseCount = countByKind(segments, 'crease')
  assert(cutCount > 80, `0201 rounded-slot cut segments should exceed rect slots, got ${cutCount}`)
  assert(creaseCount === 6, `0201 crease segments should be 6, got ${creaseCount}`)

  const topCuts = horizontalCutsAt(segments, 0)
  const bottomCuts = horizontalCutsAt(segments, W + geometry.manufacturing.height)
  assert(topCuts.length >= 4, `top edge should be split into >=4 segments, got ${topCuts.length}`)
  assert(bottomCuts.length >= 4, `bottom edge should be split into >=4 segments, got ${bottomCuts.length}`)

  for (const xi of [xW1, xL2, xW2]) {
    const leftVerts = verticalCutsAt(segments, xi - half)
    const rightVerts = verticalCutsAt(segments, xi + half)
    assert(leftVerts.length >= 2, `slot left edge expected at x=${xi - half}`)
    assert(rightVerts.length >= 2, `slot right edge expected at x=${xi + half}`)
    assert(verticalCutsAt(segments, xi).length === 0, `zero-width center slit should be removed at x=${xi}`)
  }

  assert(preview.segments.length === segments.length, 'engine preview segments should match build0201Segments')

  const formulaPreview = buildPreview(params)
  assert(formulaPreview.source === 'engine', '0201 formula preview should use engine source')
  assert(formulaPreview.segments.length === segments.length, '0201 formula preview segments match builder')

  const dxf = exportDxf(preview)
  assert(dxf.length > 500, 'DXF export should produce line entities')
  assert(dxf.includes('LINE'), 'DXF export should include LINE entities')

  const pdfBytes = buildDielinePdfBytes(preview)
  assert(pdfBytes.length > 1024, 'PDF export should exceed 1KB')
  const pdfHeader = String.fromCharCode(...pdfBytes.slice(0, 4))
  assert(pdfHeader === '%PDF', `PDF export should start with %PDF, got ${pdfHeader}`)
  const pdfBytesAgain = buildDielinePdfBytes(preview)
  assert(pdfBytesAgain.length === pdfBytes.length, 'PDF and AI should share the same byte length')

  const params0427: BoxParams = {
    ...params,
    boxCode: '0427',
    length: 200,
    width: 150,
    height: 100,
    thickness: 3,
  }
  const geo0427 = computeGeometry(params0427)
  const seg0427 = build0427Segments(geo0427)
  const blank0427 = compute0427BlankSize(200, 150, 100, 3)
  assert(countByKind(seg0427, 'cut') > 20, '0427 should produce substantial cut geometry')
  assert(countByKind(seg0427, 'crease') >= 10, '0427 should produce multiple crease lines')
  assert(blank0427.blankWidthMm === 500, '0427 blank width = L + 2W')
  assert(Math.abs(blank0427.blankHeightMm - (2 * 100 + 2 * 150 + blank0427.tuckHeightMm)) < 0.01, '0427 blank height formula')
  assert(geo0427.blankWidthMm === blank0427.blankWidthMm, '0427 geometry blank width matches helper')
  assert(geo0427.blankHeightMm === blank0427.blankHeightMm, '0427 geometry blank height matches helper')

  const params0210: BoxParams = {
    ...params,
    boxCode: '0210',
    length: 354,
    width: 354,
    height: 208,
    thickness: 3,
    dimensionType: 'manufacturing',
  }
  const geo0210 = computeGeometry(params0210)
  const seg0210 = buildFoldingShippingSegments(geo0210)
  assert(geo0210.blankWidthMm === 1441, '0210 blank width')
  assert(geo0210.blankHeightMm === 562, '0210 blank height')
  assert(countByKind(seg0210, 'crease') === 6, '0210 crease count')
  assert(countByKind(seg0210, 'cut') > countByKind(build0201Segments(geo0210), 'cut') - 20, '0210 should have interlock slots')

  const params0713: BoxParams = {
    ...params,
    boxCode: '0713',
    length: 200,
    width: 150,
    height: 100,
    thickness: 1.5,
    dimensionType: 'manufacturing',
  }
  const geo0713 = computeGeometry(params0713)
  const seg0713 = buildTuckEndSegments(geo0713)
  assert(countByKind(seg0713, 'cut') > 30, '0713 should have substantial cut geometry')
  assert(countByKind(seg0713, 'crease') >= 6, '0713 should have body creases')

  const params0716: BoxParams = {
    ...params0713,
    boxCode: '0716',
  }
  const geo0716 = computeGeometry(params0716)
  const seg0716 = buildAutoLockBottomSegments(geo0716)
  assert(countByKind(seg0716, 'cut') > countByKind(seg0713, 'cut') - 5, '0716 should include lock-bottom cuts')
  assert(countByKind(seg0716, 'crease') >= 7, '0716 should include lock crease')

  const parametricPreview = buildPreview({
    ...params,
    boxCode: '9998',
    length: 200,
    width: 80,
    height: 100,
    thickness: 1.5,
    dimensionType: 'manufacturing',
  })
  assert(parametricPreview.segments.length === 2, 'fixed asset should skip ignored entities')
  assert(parametricPreview.geometry.blankWidthMm === 100, 'fixed asset blank width uses calibrated/raw bbox')
  assert(parametricPreview.geometry.blankHeightMm === 50, 'fixed asset blank height uses calibrated/raw bbox')
  assert(parametricPreview.source === 'parametric', 'fixed asset preview marked for generic annotations')
  assert(exportDxf(parametricPreview).includes('LINE'), 'fixed asset DXF should reuse segments')
  const parametricAsset = getBoxTemplate('9998')?.activeParametricAsset
  const parametricAnnotations = getDimAnnotations(parametricPreview, 'mm', 'manufacturing', 'slotted_rsc', parametricAsset)
  assert(parametricAnnotations.length === 3, 'fixed asset template should use admin L/W/H annotations')
  assert(getDimAnnotations(parametricPreview, 'mm', 'manufacturing', 'slotted_rsc').length === 0, 'without admin annotations should not use bbox fallback')
  assert(
    parametricAnnotations.some((ann) => ann.field === 'length' && ann.displayValue === 200),
    'length annotation should use current geometry',
  )
  assert(
    parametricAnnotations.some((ann) => ann.field === 'width' && ann.displayValue === 80),
    'width annotation should use current geometry',
  )
  assert(
    parametricAnnotations.some((ann) => ann.field === 'height' && ann.displayValue === 100),
    'height annotation should use current geometry',
  )
  const lengthAnn = parametricAnnotations.find((ann) => ann.field === 'length')
  assert((lengthAnn?.dimLines?.length || 0) >= 3, 'parametric length annotation should include extension lines and dimension line')
  assert(lengthAnn?.dimLines?.some((line) => line.role === 'dimension'), 'parametric length annotation should include dimension line')
  assert((lengthAnn?.dimLines?.filter((line) => line.role === 'extension').length || 0) >= 2, 'parametric length annotation should include extension lines')
  assert(lengthAnn && lengthAnn.extents.maxX > lengthAnn.extents.minX, 'parametric annotation should expose extents for viewBox expansion')
  assert(computeDimViewBox(parametricPreview, parametricAnnotations).includes(' '), 'dim viewBox should be computable for parametric annotations')

  const near = (a: number, b: number, tolerance = 0.2) => Math.abs(a - b) <= tolerance
  const geoFromInternal = computeGeometry({ ...params, dimensionType: 'internal' })
  const geoFromManufacturing = computeGeometry({
    ...params,
    length: geoFromInternal.manufacturing.length,
    width: geoFromInternal.manufacturing.width,
    height: geoFromInternal.manufacturing.height,
    dimensionType: 'manufacturing',
  })
  assert(near(geoFromInternal.internal.length, geoFromManufacturing.internal.length), 'internal length stable across dimension type')
  assert(near(geoFromInternal.external.length, geoFromManufacturing.external.length), 'external length stable across dimension type')
  assert(near(geoFromInternal.manufacturing.length, geoFromManufacturing.manufacturing.length), 'manufacturing length stable across dimension type')
}
