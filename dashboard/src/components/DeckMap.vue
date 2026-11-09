<template>
  <div
    class="relative w-full h-full bg-slate-900 border border-slate-700 rounded-xl overflow-hidden shadow-xl"
  >
    <div ref="container" class="absolute inset-0 w-full h-full z-0"></div>
    <div
      v-if="tooltipInfo"
      class="absolute z-50 pointer-events-none deck-tooltip transition-all duration-100 ease-linear"
      :style="{ left: tooltipInfo.x + 'px', top: tooltipInfo.y + 'px' }"
      v-html="tooltipInfo.html"
    ></div>

    <div class="absolute bottom-32 right-6 flex flex-col gap-2 z-40 pointer-events-auto">
      <button 
        @click="toggleColumns" 
        class="bg-slate-800 hover:bg-slate-700 border border-slate-600 text-white p-3 rounded-full shadow-lg transition-colors flex items-center justify-center"
        :title="showColumns ? 'Nascondi colonne' : 'Mostra colonne'"
      >
        <Eye v-if="showColumns" class="w-5 h-5" />
        <EyeOff v-else class="w-5 h-5 text-slate-400" />
      </button>
      <button 
        @click="resetMap" 
        class="bg-blue-600 hover:bg-blue-500 text-white p-3 rounded-full shadow-lg transition-colors flex items-center justify-center"
        title="Reset mappa"
      >
        <RefreshCw class="w-5 h-5" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { Deck } from "@deck.gl/core";
import { PathLayer, ColumnLayer, BitmapLayer } from "@deck.gl/layers";
import { TileLayer } from "@deck.gl/geo-layers";
import { Eye, EyeOff, RefreshCw } from 'lucide-vue-next';

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  viewState: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(["update:viewState"]);

const defaultViewState = {
  longitude: -69.150005,
  latitude: -24.270004,
  zoom: 12,
  pitch: 45,
  bearing: -20
};

const container = ref(null);
let deckInstance = null;
const tooltipInfo = ref(null);
const showColumns = ref(true);

const resetMap = () => {
  const pts = props.data.filter(d => d.position && d.position.length >= 2);
  if (!pts.length) {
    emit("update:viewState", { ...defaultViewState });
    return;
  }
  const lons = pts.map(d => d.position[0]);
  const lats = pts.map(d => d.position[1]);
  emit("update:viewState", {
    ...defaultViewState,
    longitude: (Math.min(...lons) + Math.max(...lons)) / 2,
    latitude: (Math.min(...lats) + Math.max(...lats)) / 2
  });
};

const toggleColumns = () => {
  showColumns.value = !showColumns.value;
  updateLayers(props.data);
};

const getColorFromPOF = (pof, opacity) => {
  if (pof >= 0.8) return [239, 68, 68, opacity];
  if (pof >= 0.5) return [249, 115, 22, opacity];
  if (pof >= 0.2) return [250, 204, 21, opacity];
  return [52, 211, 153, Math.min(opacity, 200)]; // Adjust max opacity for lower risk
};

onMounted(() => {
  if (!container.value) return;

  deckInstance = new Deck({
    parent: container.value,
    initialViewState: props.viewState, // Use initialViewState! Handled internally by Deck. GL
    controller: true,
    onViewStateChange: ({ viewState }) => {
      emit("update:viewState", viewState);
    },
    getTooltip: ({ object, x, y }) => {
      if (!object) {
        tooltipInfo.value = null;
        return null;
      }
      const html = `
        <div class="font-bold text-lg mb-1 border-b border-slate-600 pb-1">Metro (KP): ${object.kp}</div>
        <div class="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-sm">
            <div class="text-slate-400">Tipo:</div>
            <div class="text-white font-medium">${object.type || "-"}</div>
            <div class="text-slate-400">POF:</div>
            <div class="font-bold ${object.pof >= 0.8 ? "text-red-400" : "text-white"}">${object.pof}</div>
            <div class="text-slate-400">Profondità Danno:</div>
            <div class="text-white font-medium">${object.depth} mm</div>
            <div class="text-slate-400">Gravità:</div>
            <div class="text-white font-medium">${object.severity || "-"}</div>
            <div class="text-slate-400">Sorgente:</div>
            <div class="text-white font-medium text-xs break-all truncate col-span-2 mt-1 leading-tight max-w-xs">${object.source || "-"}</div>
        </div>
      `;
      tooltipInfo.value = { x, y, html };
      return null;
    }
  });

  updateLayers(props.data);
});

watch(
  () => props.viewState,
  newViewState => {
    if (deckInstance) {
      // Just update initialViewState. Controller handles local transitions usually.
      deckInstance.setProps({ initialViewState: newViewState });
    }
  },
  { deep: true }
);

watch(
  () => props.data,
  newData => {
    if (deckInstance) {
      updateLayers(newData);
    }
  },
  { deep: true, immediate: true }
);

function updateLayers(mapData) {
  if (!deckInstance) return;

  const validData = mapData.filter(d =>
    Boolean(d.position && d.position.length >= 2 && d.position[0] !== 0 && d.position[1] !== 0)
  );
  const lineData = [...validData]
    .sort((a, b) => a.kp - b.kp)
    .map(d => d.position);

  deckInstance.setProps({
    layers: [
      new TileLayer({
        id: "base-map",
        data: "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/tiles/256/{z}/{x}/{y}@2x?access_token=pk.eyJ1Ijoicm9uemltIiwiYSI6ImNqdDdtOWIzZDBmODA0OWp6bThxbGZhYXgifQ.t4KKKWA-zOe6OLzFhuT0bw",
        minZoom: 0,
        maxZoom: 19,
        renderSubLayers: props => {
          const { west, south, east, north } = props.tile.bbox;
          return new BitmapLayer(props, {
            data: null,
            image: props.data,
            bounds: [west, south, east, north]
          });
        }
      }),
      new PathLayer({
        id: "pipeline-path",
        data: [{ path: lineData }],
        pickable: true,
        widthScale: 1,
        widthMinPixels: 2,
        getColor: [200, 200, 200, 180]
      }),
      new ColumnLayer({
        id: "anomalies-3d",
        data: validData,
        diskResolution: 12,
        radius: 4,
        elevationScale: showColumns.value ? 200 : 10,
        extruded: true,
        pickable: true,
        getPosition: d => d.position,
        getFillColor: d => getColorFromPOF(d.pof, showColumns.value ? 255 : 50),
        getLineColor: [0, 0, 0, 0],
        getElevation: d => d.depth || 0.1,
        // Update layer when parameters change
        updateTriggers: {
          getFillColor: [showColumns.value],
          elevationScale: [showColumns.value]
        }
      })
    ]
  });
}

onUnmounted(() => {
  if (deckInstance) {
    deckInstance.finalize();
  }
});
</script>

<style>
.deck-tooltip {
  font-family:
    system-ui,
    -apple-system,
    sans-serif;
  padding: 12px;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid #334155;
  border-radius: 8px;
  color: #f8fafc;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  transform: translate(-50%, -120%); /* slightly above cursor */
}
</style>
