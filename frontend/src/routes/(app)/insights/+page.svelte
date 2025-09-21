<script lang="ts">
  type Row = {
    company: { id: number; name: string };
    year: number;
    ghg_total_value?: number;
    energy_consumption_value?: number;
    waste_generated_value?: number;
  };

  let rows: Row[] = $state([]);
  let loading: boolean = $state(false);

  async function loadAll() {
    loading = true;
    try {
      const res = await fetch('/api/vsme-register/', { credentials: 'include' });
      if (res.ok) rows = await res.json();
    } finally {
      loading = false;
    }
  }

  function sum(arr: (number | undefined)[]): number {
    return arr.reduce((s, v) => s + (Number(v) || 0), 0);
  }

  function fmt(n: number): string {
    const x = Number(n || 0);
    return x.toLocaleString();
  }

  function byYearSum(accessor: (r: Row) => number | undefined): Array<{ yr: number; val: number }> {
    const m = new Map<number, number>();
    for (const r of rows) {
      const v = Number(accessor(r) || 0);
      if (!m.has(r.year)) m.set(r.year, 0);
      m.set(r.year, m.get(r.year)! + v);
    }
    return Array.from(m.entries()).map(([yr, val]) => ({ yr, val })).sort((a, b) => a.yr - b.yr);
  }

  // KPIs (portfolio-wide totals)
  let totalGHG = $derived(sum(rows.map((r) => r.ghg_total_value)));
  let totalEnergy = $derived(sum(rows.map((r) => r.energy_consumption_value)));
  let totalWaste = $derived(sum(rows.map((r) => r.waste_generated_value)));

  // Charts: sums by year for the three metrics
  let ghgSeries = $derived(byYearSum((r) => r.ghg_total_value));
  let energySeries = $derived(byYearSum((r) => r.energy_consumption_value));
  let wasteSeries = $derived(byYearSum((r) => r.waste_generated_value));

  function toPoints(series: Array<{ yr: number; val: number }>) {
    const n = series.length;
    const maxVal = series.length ? Math.max(...series.map((p) => p.val)) : 0;
    const scale = maxVal > 0 ? 180 / maxVal : 0;
    return series.map((p, i) => ({
      x: 40 + (n > 1 ? i * (420 / (n - 1)) : 0),
      y: 200 - p.val * scale,
      yr: p.yr,
      val: p.val
    }));
  }

  let ghgPoints = $derived(toPoints(ghgSeries));
  let energyPoints = $derived(toPoints(energySeries));
  let wastePoints = $derived(toPoints(wasteSeries));

  $effect(() => { loadAll(); });
</script>

<div class="p-6 bg-base-200/40 min-h-screen">
  <div class="mx-auto max-w-6xl space-y-6">
    <div class="flex items-end justify-between">
      <h1 class="text-2xl font-semibold">Insights</h1>
      <div class="text-sm opacity-70">Aggregated across your entire portfolio</div>
    </div>
    {#if loading}
      <div>Loading…</div>
    {:else}
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="rounded-box border border-base-300 p-4 bg-base-100 shadow-sm">
          <div class="text-sm opacity-70">Total GHG emissions</div>
          <div class="text-3xl font-semibold">{fmt(totalGHG)}</div>
        </div>
        <div class="rounded-box border border-base-300 p-4 bg-base-100 shadow-sm">
          <div class="text-sm opacity-70">Total energy consumption</div>
          <div class="text-3xl font-semibold">{fmt(totalEnergy)}</div>
        </div>
        <div class="rounded-box border border-base-300 p-4 bg-base-100 shadow-sm">
          <div class="text-sm opacity-70">Total waste generated</div>
          <div class="text-3xl font-semibold">{fmt(totalWaste)}</div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="rounded-box border border-base-300 p-4 bg-base-100 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <div class="font-semibold">GHG by year</div>
            <div class="badge">Sum</div>
          </div>
        <svg viewBox="0 0 500 220" class="w-full h-52">
          {#if ghgPoints.length === 0}
            <text x="10" y="20">No data</text>
          {:else}
            {#each ghgPoints as p, i}
              {#if i > 0}
                <line x1={ghgPoints[i - 1].x} y1={ghgPoints[i - 1].y} x2={p.x} y2={p.y} stroke="#2563eb" stroke-width="2" />
              {/if}
              <circle cx={p.x} cy={p.y} r="3" fill="#2563eb" />
              <text x={p.x} y="210" font-size="10">{p.yr}</text>
            {/each}
          {/if}
        </svg>
          <div class="mt-1 text-xs opacity-70">Totals per year</div>
        </div>

        <div class="rounded-box border border-base-300 p-4 bg-base-100 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <div class="font-semibold">Energy by year</div>
            <div class="badge">Sum</div>
          </div>
        <svg viewBox="0 0 500 220" class="w-full h-52">
          {#if energyPoints.length === 0}
            <text x="10" y="20">No data</text>
          {:else}
            {#each energyPoints as p, i}
              {#if i > 0}
                <line x1={energyPoints[i - 1].x} y1={energyPoints[i - 1].y} x2={p.x} y2={p.y} stroke="#16a34a" stroke-width="2" />
              {/if}
              <circle cx={p.x} cy={p.y} r="3" fill="#16a34a" />
              <text x={p.x} y="210" font-size="10">{p.yr}</text>
            {/each}
          {/if}
        </svg>
          <div class="mt-1 text-xs opacity-70">Totals per year</div>
        </div>

        <div class="rounded-box border border-base-300 p-4 bg-base-100 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <div class="font-semibold">Waste by year</div>
            <div class="badge">Sum</div>
          </div>
        <svg viewBox="0 0 500 220" class="w-full h-52">
          {#if wastePoints.length === 0}
            <text x="10" y="20">No data</text>
          {:else}
            {#each wastePoints as p, i}
              {#if i > 0}
                <line x1={wastePoints[i - 1].x} y1={wastePoints[i - 1].y} x2={p.x} y2={p.y} stroke="#f59e0b" stroke-width="2" />
              {/if}
              <circle cx={p.x} cy={p.y} r="3" fill="#f59e0b" />
              <text x={p.x} y="210" font-size="10">{p.yr}</text>
            {/each}
          {/if}
        </svg>
          <div class="mt-1 text-xs opacity-70">Totals per year</div>
        </div>
      </div>
    {/if}
  </div>
</div>


