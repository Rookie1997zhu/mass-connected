<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  previewMesh: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const { t } = useI18n()
const containerRef = ref(null)

let renderer = null
let scene = null
let camera = null
let controls = null
let animationId = null
let resizeObserver = null

const disposeObject = (obj) => {
  if (!obj) return
  obj.traverse?.((child) => {
    if (child.geometry) child.geometry.dispose()
    if (child.material) {
      if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose())
      else child.material.dispose()
    }
  })
  if (obj.parent) obj.parent.remove(obj)
}

const fitCamera = (object, cam, ctrl) => {
  const THREE = window.__stpThree
  if (!THREE || !object || !cam) return
  const box = new THREE.Box3().setFromObject(object)
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const maxDim = Math.max(size.x, size.y, size.z, 1)
  const dist = maxDim * 2.2
  cam.position.set(center.x + dist, center.y + dist * 0.6, center.z + dist)
  cam.lookAt(center)
  if (ctrl) {
    ctrl.target.copy(center)
    ctrl.update()
  }
}

const loadMesh = async () => {
  if (!containerRef.value || !props.previewMesh?.data) return

  try {
    const [THREE, { STLLoader }, { OrbitControls }] = await Promise.all([
      import('three'),
      import('three/examples/jsm/loaders/STLLoader.js'),
      import('three/examples/jsm/controls/OrbitControls.js'),
    ])
    window.__stpThree = THREE

    const width = containerRef.value.clientWidth || 400
    const height = containerRef.value.clientHeight || 320

    if (!renderer) {
      scene = new THREE.Scene()
      scene.background = new THREE.Color(0xf5f5f5)
      camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)
      renderer = new THREE.WebGLRenderer({ antialias: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
      renderer.setSize(width, height)
      containerRef.value.appendChild(renderer.domElement)
      controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.dampingFactor = 0.08

      const ambient = new THREE.AmbientLight(0xffffff, 0.65)
      const dir = new THREE.DirectionalLight(0xffffff, 0.85)
      dir.position.set(2, 3, 4)
      scene.add(ambient, dir)

      const grid = new THREE.GridHelper(200, 20, 0xcccccc, 0xe8e8e8)
      grid.position.y = 0
      scene.add(grid)

      const animate = () => {
        animationId = requestAnimationFrame(animate)
        controls?.update()
        renderer?.render(scene, camera)
      }
      animate()
    } else {
      renderer.setSize(width, height)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }

    const old = scene.getObjectByName('stp-mesh')
    if (old) disposeObject(old)

    const binary = atob(props.previewMesh.data)
    const buffer = new ArrayBuffer(binary.length)
    const view = new Uint8Array(buffer)
    for (let i = 0; i < binary.length; i += 1) view[i] = binary.charCodeAt(i)

    const loader = new STLLoader()
    const head = new TextDecoder().decode(view.slice(0, Math.min(80, view.length))).trimStart().toLowerCase()
    const stlGeometry = head.startsWith('solid')
      ? loader.parse(new TextDecoder().decode(view))
      : loader.parse(buffer)
    stlGeometry.computeVertexNormals()
    const material = new THREE.MeshStandardMaterial({ color: 0x9aa3ad, metalness: 0.15, roughness: 0.55 })
    const mesh = new THREE.Mesh(stlGeometry, material)
    mesh.name = 'stp-mesh'
    scene.add(mesh)
    fitCamera(mesh, camera, controls)
  } catch (err) {
    console.error('[StpViewer3d] failed to load mesh', err)
  }
}

const initScene = async () => {
  if (props.previewMesh?.data) await loadMesh()
}

watch(() => props.previewMesh?.data, () => {
  if (props.previewMesh?.data) loadMesh()
  else {
    const old = scene?.getObjectByName('stp-mesh')
    if (old) disposeObject(old)
  }
})

onMounted(() => {
  initScene()
  if (containerRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      if (!containerRef.value || !renderer || !camera) return
      const w = containerRef.value.clientWidth
      const h = containerRef.value.clientHeight
      if (w && h) {
        renderer.setSize(w, h)
        camera.aspect = w / h
        camera.updateProjectionMatrix()
      }
    })
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  if (animationId) cancelAnimationFrame(animationId)
  resizeObserver?.disconnect()
  if (scene) {
    const old = scene.getObjectByName('stp-mesh')
    if (old) disposeObject(old)
  }
  controls?.dispose()
  renderer?.dispose()
  if (renderer?.domElement?.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement)
  renderer = null
  scene = null
  camera = null
  controls = null
})
</script>

<template>
  <div class="stp-viewer">
    <div ref="containerRef" class="stp-viewer__canvas" />
    <div v-if="loading" class="stp-viewer__overlay">{{ t('injectionQuote.viewerLoading') }}</div>
    <div v-else-if="!previewMesh?.data" class="stp-viewer__overlay stp-viewer__overlay--hint">
      <p>{{ t('injectionQuote.viewerPlaceholder') }}</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stp-viewer {
  position: relative;
  width: 100%;
  min-height: 280px;
  border: 1px solid #111;
  background: #fafafa;
}
.stp-viewer__canvas {
  width: 100%;
  height: 320px;
}
.stp-viewer__overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.75);
  font-size: 0.9rem;
  pointer-events: none;
  &--hint p { margin: 0; color: var(--color-text-muted); text-align: center; padding: 1rem; }
}
</style>
