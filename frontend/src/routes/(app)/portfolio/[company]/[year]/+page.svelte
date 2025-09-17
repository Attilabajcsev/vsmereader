<script lang="ts">
  import { goto } from '$app/navigation';
  let row: any = $state(null);
  let loading: boolean = $state(false);

  function getParams(): { company: string; year: string } {
    const m = globalThis.location?.pathname.match(/\/portfolio\/(\d+)\/(\d{4})/);
    return { company: m ? m[1] : '', year: m ? m[2] : '' };
  }

  async function load() {
    const { company, year } = getParams();
    if (!company || !year) return;
    loading = true;
    try {
      const res = await fetch(`/api/register/${company}/${year}/`, { credentials: 'include' });
      if (res.ok) row = await res.json();
    } finally {
      loading = false;
    }
  }

  $effect(() => { load(); });
</script>

<div class="p-6 space-y-4">
  <button class="btn btn-ghost" onclick={() => goto('/portfolio')}>← Back</button>
  {#if !row}
    <div>{loading ? 'Loading…' : 'Not found'}</div>
  {:else}
    <h1 class="text-2xl font-semibold">{row.company?.name} — {row.year}</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="rounded border p-4 space-y-2">
        <div class="font-semibold">Overview</div>
        <div>Entity: {row.entity_identifier || '—'}</div>
        <div>Completeness: {row.completeness_score}%</div>
        {#if row.last_report}
          <div>Last report: <a class="link" href={`/reports/${row.last_report}`}>#{row.last_report}</a></div>
        {/if}
        <div>Updated: {new Date(row.updated_at).toLocaleString()}</div>
      </div>
      <div class="rounded border p-4 space-y-2">
        <div class="font-semibold">Core metrics</div>
        <div>Employees: {row.employees_value ?? '—'} {row.employees_unit}</div>
        <div>GHG total: {row.ghg_total_value ?? '—'} {row.ghg_total_unit}</div>
        <div>Scope 1: {row.ghg_scope1_value ?? '—'} {row.ghg_scope1_unit}</div>
        <div>Scope 2: {row.ghg_scope2_value ?? '—'} {row.ghg_scope2_unit}</div>
        <div>Energy: {row.energy_consumption_value ?? '—'} {row.energy_consumption_unit}</div>
        <div>Renewables: {row.renewable_energy_share_value ?? '—'} {row.renewable_energy_share_unit}</div>
        <div>Water withdrawal: {row.water_withdrawal_value ?? '—'} {row.water_withdrawal_unit}</div>
        <div>Water discharge: {row.water_discharge_value ?? '—'} {row.water_discharge_unit}</div>
        <div>Waste generated: {row.waste_generated_value ?? '—'} {row.waste_generated_unit}</div>
        <div>Hazardous waste: {row.hazardous_waste_value ?? '—'} {row.hazardous_waste_unit}</div>
        <div>Non-hazardous waste: {row.non_hazardous_waste_value ?? '—'} {row.non_hazardous_waste_unit}</div>
      </div>
    </div>

    <div class="rounded border p-4 space-y-2">
      <div class="font-semibold">Source concepts</div>
      {#if row.source_concepts}
        <div class="overflow-x-auto">
          <table class="table">
            <thead><tr><th>Code</th><th>Concept</th><th>Unit</th></tr></thead>
            <tbody>
              {#each Object.entries(row.source_concepts) as [code, src]}
                <tr>
                  <td>{code}</td>
                  <td class="max-w-[600px] truncate" title={src?.concept}>{src?.concept}</td>
                  <td>{src?.unit}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div>No sources recorded.</div>
      {/if}
    </div>
  {/if}
</div>


