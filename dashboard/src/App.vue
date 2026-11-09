<template>
  <div
    class="w-screen h-screen overflow-hidden bg-slate-900 text-white font-sans relative"
  >
    <DeckMap
      v-if="pipelineData.length > 0"
      :data="pipelineData"
      :route="pipelineRoute"
      :viewState="viewState"
      @update:viewState="val => (viewState = val)"
    />
    <div
      v-else
      class="absolute inset-0 flex items-center justify-center bg-slate-900 z-50"
    >
      <div class="text-xl animate-pulse text-slate-400">
        Caricamento dati pipeline...
      </div>
    </div>

    <!-- UI Sovrapposta: Header -->
    <div
      class="absolute top-0 left-0 right-0 p-6 pointer-events-none z-10 flex justify-between items-start"
    >
      <div>
        <h1
          class="text-3xl font-black tracking-tight text-white drop-shadow-md"
        >
          Risk<span class="text-blue-500">Map</span> 3D
        </h1>
        <div class="mt-2 pointer-events-auto flex items-center gap-2">
          <MapPin class="w-4 h-4 text-slate-300" />
          <select
            v-if="zones.length > 0"
            v-model="selectedZoneId"
            class="bg-slate-800/80 text-white rounded-lg border border-slate-700 px-3 py-1.5 text-sm shadow-lg outline-none backdrop-blur-md cursor-pointer hover:bg-slate-700 transition"
          >
            <option v-for="zone in zones" :key="zone.id" :value="zone.id">
              {{ zone.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Controlli vista (pointer-events-auto per permettere i click) -->
      <div
        class="pointer-events-auto bg-slate-800/80 backdrop-blur-md rounded-lg p-1 border border-slate-700 flex flex-col gap-1 shadow-lg"
      >
        <button
          @click="set2DView"
          class="p-2 hover:bg-slate-700 rounded text-slate-300 transition-colors"
          title="Vista 2D (Dall'alto)"
        >
          <MapIcon class="w-5 h-5" />
        </button>
        <button
          @click="set3DView"
          class="p-2 hover:bg-slate-700 rounded text-slate-300 transition-colors"
          title="Vista 3D"
        >
          <Box class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- UI Sovrapposta: Dashboard laterale -->
    <div
      class="absolute top-28 left-6 w-72 flex flex-col gap-4 pointer-events-auto z-10"
    >
      <MetricCard
        title="Punti Critici Rilevati"
        :value="stats.criticalCount"
        icon="alert-triangle"
        color-class="text-red-500"
      />
      <MetricCard
        title="POF Massimo"
        :value="stats.maxPof"
        icon="activity"
        color-class="text-orange-500"
      />
      <MetricCard
        title="Profondità Media Danno"
        :value="stats.avgDepth"
        unit="mm"
        icon="arrow-down-to-line"
        color-class="text-blue-400"
      />

      <div
        class="bg-slate-800/80 backdrop-blur-md p-4 rounded-xl border border-slate-700 shadow-lg mt-2"
      >
        <h3
          class="text-sm font-bold text-slate-200 mb-2 flex items-center gap-2"
        >
          <Info class="w-4 h-4 text-slate-400" />
          Info Ispezione
        </h3>
        <ul class="text-xs text-slate-400 space-y-2">
          <li>
            <strong class="text-slate-300">Totale Record:</strong>
            {{ pipelineData.length }} misurazioni
          </li>
          <li>
            <strong class="text-slate-300">Base Spessore (WT):</strong> 9.5 mm /
            12.7 mm
          </li>
          <li>
            <strong class="text-slate-300">Spessore Critico:</strong> ~ 3.8 mm
            (var.)
          </li>
          <li>
            <strong class="text-slate-300">Lunghezza Valutata:</strong>
            {{ stats.lengthKm }} km
          </li>
        </ul>
      </div>
    </div>

    <!-- UI Sovrapposta: Legenda POF -->
    <div
      class="absolute bottom-6 right-6 bg-slate-800/90 backdrop-blur-md p-4 rounded-xl border border-slate-700 shadow-lg pointer-events-auto z-10"
    >
      <h3 class="text-sm font-bold text-slate-200 mb-3">Gravità (POF)</h3>
      <div class="space-y-2 text-xs">
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-red-500"></span
          ><span class="text-slate-300">Critico (≥ 0.8)</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-orange-500"></span
          ><span class="text-slate-300">Alto (0.5 - 0.8)</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-yellow-400"></span
          ><span class="text-slate-300">Medio (0.2 - 0.5)</span>
        </div>
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full bg-emerald-400"></span
          ><span class="text-slate-300">Basso (&lt; 0.2)</span>
        </div>
      </div>
    </div>

    <!-- Istruzioni interazione -->
    <div
      class="absolute bottom-6 left-1/2 transform -translate-x-1/2 bg-slate-900/60 backdrop-blur px-4 py-2 rounded-full text-xs text-slate-300 font-medium border border-slate-700 pointer-events-none tracking-wide text-center z-10 shadow-lg"
    >
      Trascina per spostarti • Ctrl + Trascina per ruotare (3D)<br />
      Passa sopra le colonne per i dettagli
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from "vue";
import { MapPin, Map as MapIcon, Box, Info } from "lucide-vue-next";
import DeckMap from "./components/DeckMap.vue";
import MetricCard from "./components/MetricCard.vue";

const zones = ref([]);
const selectedZoneId = ref(null);

const pipelineData = computed(() => {
  if (!zones.value.length || !selectedZoneId.value) return [];
  const z = zones.value.find(z => z.id === selectedZoneId.value);
  return z ? z.data : [];
});

const pipelineRoute = computed(() => {
  const z = zones.value.find(z => z.id === selectedZoneId.value);
  return z && z.route ? z.route : [];
});

const viewState = ref({
  longitude: -69.150005,
  latitude: -24.270004,
  zoom: 12,
  pitch: 45,
  bearing: -20
});

const stats = computed(() => {
  const data = pipelineData.value;
  if (!data || data.length === 0) {
    return {
      criticalCount: 0,
      avgDepth: "0.0",
      maxPof: "0.000",
      lengthKm: "0.0"
    };
  }

  const criticalCount = data.filter(d => d.pof >= 0.8).length;
  const sumDepth = data.reduce((acc, curr) => acc + (curr.depth || 0), 0);
  const avgDepth = (sumDepth / data.length).toFixed(1);
  const maxPof = Math.max(...data.map(d => d.pof || 0)).toFixed(3);

  const minKp = Math.min(...data.map(d => d.kp || 0));
  const maxKp = Math.max(...data.map(d => d.kp || 0));
  const lengthKm = ((maxKp - minKp) / 1000).toFixed(1);

  return { criticalCount, avgDepth, maxPof, lengthKm };
});

watch(selectedZoneId, newId => {
  const zone = zones.value.find(z => z.id === newId);
  if (zone && zone.data && zone.data.length > 0) {
    const pts = zone.route && zone.route.length
      ? zone.route
      : zone.data.filter(d => d.position && d.position.length >= 2).map(d => d.position);
    if (pts.length) {
      const lons = pts.map(p => p[0]);
      const lats = pts.map(p => p[1]);
      const lat = (Math.min(...lats) + Math.max(...lats)) / 2;
      const span = Math.max(
        (Math.max(...lons) - Math.min(...lons)) * Math.cos((lat * Math.PI) / 180),
        Math.max(...lats) - Math.min(...lats),
        1e-4
      );
      viewState.value = {
        ...viewState.value,
        longitude: (Math.min(...lons) + Math.max(...lons)) / 2,
        latitude: lat,
        zoom: Math.max(3, Math.min(14, Math.log2(1200 / span) - 1.5)),
        transitionDuration: 2000
      };
    }
  }
});

onMounted(async () => {
  try {
    const res = await fetch(`${import.meta.env.BASE_URL}pipeline_data.json`);
    if (!res.ok) throw new Error("Could not fetch data");
    const rawData = await res.json();

    // Assumiamo che il json ritorni un array di zone
    zones.value = rawData;
    if (rawData.length > 0) {
      selectedZoneId.value = rawData[0].id;
    }
  } catch (error) {
    console.error("Error loading data:", error);
  }
});

const set2DView = () => {
  viewState.value = {
    ...viewState.value,
    pitch: 0,
    bearing: 0,
    transitionDuration: 1000
  };
};

const set3DView = () => {
  viewState.value = {
    ...viewState.value,
    pitch: 45,
    bearing: -20,
    transitionDuration: 1000
  };
};
</script>
<style>
body {
  margin: 0;
  overflow: hidden;
}
</style>
