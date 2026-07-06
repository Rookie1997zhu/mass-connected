declare module 'makerjs' {
  const makerjs: {
    paths: {
      Line: new (origin: [number, number], end: [number, number]) => unknown
    }
    exporter: {
      toDXF: (model: unknown) => string
      toSVG: (model: unknown, options?: { units?: unknown }) => string
    }
    unitType: {
      Millimeter: unknown
    }
    IModel: unknown
    IPathMap: unknown
  }
  export default makerjs
}
