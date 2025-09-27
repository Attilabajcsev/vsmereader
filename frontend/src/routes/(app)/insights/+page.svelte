<script lang="ts">
  type InsightsData = {
    status_tiles: {
      companies_count: number;
      validated_reports_count: number;
      latest_submission: string | null;
      portfolio_completeness: number;
    };
    kpi_trends: {
      ghg_by_year: Array<{ year: number; value: number }>;
      energy_by_year: Array<{ year: number; value: number }>;
      waste_by_year: Array<{ year: number; value: number }>;
      ghg_per_employee: Array<{ year: number; value: number }>;
    };
    quality_snapshot: {
      units_analysis: Record<string, {
        target_unit: string;
        most_common_unit: string;
        consistency_pct: number;
        status: string;
      }>;
      portfolio_completeness: number;
      distribution_data: {
        year: number;
        values: number[];
        count: number;
      } | null;
    };
  };

  let data: InsightsData | null = $state(null);
  let loading: boolean = $state(false);

  async function loadInsights() {
    loading = true;
    try {
      const res = await fetch('/api/insights/aggregated/', { credentials: 'include' });
      if (res.ok) {
        const responseData = await res.json();
        console.log('Insights data loaded:', responseData);
        data = responseData;
      } else {
        console.error('Failed to load insights:', res.status, res.statusText);
      }
    } catch (error) {
      console.error('Error loading insights:', error);
    } finally {
      loading = false;
    }
  }

  function formatNumber(n: number): string {
    return n.toLocaleString();
  }

  function formatDate(isoString: string | null): string {
    if (!isoString) return 'No data';
    return new Date(isoString).toLocaleDateString();
  }

  function createLineChart(data: Array<{ year: number; value: number }>, color: string = '#2563eb') {
    if (data.length === 0) return { 
      pathData: '', 
      points: [] as Array<{ x: number; y: number; year: number; value: number }>, 
      color, 
      width: 460, 
      height: 160, 
      padding: 40 
    };
    
    try {
      const width = 460;
      const height = 160;
      const padding = 40;
      
      // Filter out invalid data
      const validData = data.filter(d => 
        typeof d.year === 'number' && 
        typeof d.value === 'number' && 
        !isNaN(d.year) && 
        !isNaN(d.value) && 
        isFinite(d.year) && 
        isFinite(d.value)
      );
      
      if (validData.length === 0) {
        return { 
          pathData: '', 
          points: [], 
          color, 
          width, 
          height, 
          padding 
        };
      }
      
      const years = validData.map(d => d.year);
      const values = validData.map(d => d.value);
      const minYear = Math.min(...years);
      const maxYear = Math.max(...years);
      const minValue = Math.min(...values);
      const maxValue = Math.max(...values);
      
      // Handle edge cases for scaling
      const yearRange = maxYear - minYear;
      const valueRange = maxValue - minValue;
      
      const xScale = (year: number) => {
        if (yearRange === 0) return width / 2; // Center if single year
        return padding + ((year - minYear) / yearRange) * (width - 2 * padding);
      };
      
      const yScale = (value: number) => {
        if (valueRange === 0) return height / 2; // Center if all values same
        return height - padding - ((value - minValue) / valueRange) * (height - 2 * padding);
      };
      
      let pathData = '';
      const points = validData.map((d, i) => {
        const x = xScale(d.year);
        const y = yScale(d.value);
        
        // Ensure coordinates are valid
        if (!isFinite(x) || !isFinite(y)) {
          console.warn('Invalid chart coordinates:', { x, y, year: d.year, value: d.value });
          return { x: padding, y: height - padding, year: d.year, value: d.value };
        }
        
        if (i === 0) {
          pathData += `M ${x} ${y}`;
        } else {
          pathData += ` L ${x} ${y}`;
        }
        return { x, y, year: d.year, value: d.value };
      });
      
      return { pathData, points, color, width, height, padding };
    } catch (error) {
      console.error('Error creating line chart:', error, data);
      return { 
        pathData: '', 
        points: [], 
        color, 
        width: 460, 
        height: 160, 
        padding: 40 
      };
    }
  }

  function createHistogram(values: number[]) {
    const width = 320;
    const height = 160;
    const padding = 30;
    
    if (values.length === 0) return { 
      bars: [] as Array<{ x: number; y: number; width: number; height: number; count: number; min: number; max: number }>, 
      width, 
      height, 
      binCount: 0, 
      valueCount: 0 
    };
    
    try {
      // Filter out invalid values
      const validValues = values.filter(v => 
        typeof v === 'number' && 
        !isNaN(v) && 
        isFinite(v)
      );
      
      if (validValues.length === 0) {
        return { 
          bars: [], 
          width, 
          height, 
          binCount: 0, 
          valueCount: 0 
        };
      }
      
      // Create bins
      const min = Math.min(...validValues);
      const max = Math.max(...validValues);
      const range = max - min;
      
      // Handle case where all values are the same
      if (range === 0) {
        const singleBar = {
          x: padding,
          y: padding,
          width: width - 2 * padding,
          height: height - 2 * padding,
          count: validValues.length,
          min: min,
          max: max
        };
        return { 
          bars: [singleBar], 
          width, 
          height, 
          binCount: 1, 
          valueCount: validValues.length 
        };
      }
      
      const binCount = Math.min(8, Math.ceil(Math.sqrt(validValues.length)));
      const binSize = range / binCount;
      
      const bins = Array(binCount).fill(0).map((_, i) => ({
        min: min + i * binSize,
        max: min + (i + 1) * binSize,
        count: 0
      }));
      
      // Count values in bins
      validValues.forEach(val => {
        const binIndex = Math.min(Math.floor((val - min) / binSize), binCount - 1);
        bins[binIndex].count++;
      });
      
      const maxCount = Math.max(...bins.map(b => b.count));
      const barWidth = (width - 2 * padding) / binCount;
      
      const bars = bins.map((bin, i) => ({
        x: padding + i * barWidth,
        y: height - padding - (maxCount > 0 ? (bin.count / maxCount) * (height - 2 * padding) : 0),
        width: barWidth * 0.8,
        height: maxCount > 0 ? (bin.count / maxCount) * (height - 2 * padding) : 0,
        count: bin.count,
        min: bin.min,
        max: bin.max
      }));
      
      return { bars, width, height, binCount, valueCount: validValues.length };
    } catch (error) {
      console.error('Error creating histogram:', error, values);
      return { 
        bars: [], 
        width, 
        height, 
        binCount: 0, 
        valueCount: 0 
      };
    }
  }

  $effect(() => { loadInsights(); });
</script>

<div class="p-6 bg-base-200/40 min-h-screen">
  <div class="mx-auto max-w-7xl space-y-6">
    <!-- Header -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-bold">Indsigter</h1>
        <p class="text-base-content/70 mt-1">Overblik over din porteføljes ESG-præstation på tværs af alle rapporter</p>
      </div>
      <div class="text-sm opacity-70">Aggregeret på tværs af hele din portefølje</div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="loading loading-spinner loading-lg"></div>
        <span class="ml-3">Indlæser indsigter...</span>
      </div>
    {:else if data}
      <!-- Row 1: Status Tiles -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
          <div class="text-2xl font-bold text-primary">{formatNumber(data.status_tiles.companies_count)}</div>
          <div class="text-sm text-base-content/70 mt-1">Virksomheder</div>
          <div class="text-xs text-base-content/50 mt-2">Antal unikke virksomheder i portefølje</div>
        </div>
        
        <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
          <div class="text-2xl font-bold text-success">{formatNumber(data.status_tiles.validated_reports_count)}</div>
          <div class="text-sm text-base-content/70 mt-1">Validerede rapporter</div>
          <div class="text-xs text-base-content/50 mt-2">Samlet antal validerede rapporter</div>
        </div>
        
        <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
          <div class="text-2xl font-bold text-info">{formatDate(data.status_tiles.latest_submission)}</div>
          <div class="text-sm text-base-content/70 mt-1">Seneste indsendelse</div>
          <div class="text-xs text-base-content/50 mt-2">Nyeste validerede rapport</div>
        </div>
        
        <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
          <div class="text-2xl font-bold text-warning">{data.status_tiles.portfolio_completeness.toFixed(1)}%</div>
          <div class="text-sm text-base-content/70 mt-1">Portefølje fuldstændighed</div>
          <div class="text-xs text-base-content/50 mt-2">Gennemsnitlig fuldstændighedsscore</div>
        </div>
      </div>

      <!-- Row 2: KPI Trend Charts -->
      <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
        <h2 class="text-xl font-semibold mb-4">KPI-tendenser efter år</h2>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- GHG Chart -->
          <div class="space-y-2">
            <h3 class="font-medium">Samlet drivhusgasudledning (tCO₂e)</h3>
            {#if data.kpi_trends.ghg_by_year.length >= 2}
              {@const chart = createLineChart(data.kpi_trends.ghg_by_year, '#dc2626')}
              {#if chart && chart.pathData}
                <div class="h-48 bg-base-200 rounded p-2">
                  <svg viewBox="0 0 {chart.width} {chart.height}" class="w-full h-full">
                    <!-- Grid lines -->
                    <defs>
                      <pattern id="grid" width="40" height="20" patternUnits="userSpaceOnUse">
                        <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#e5e7eb" stroke-width="0.5"/>
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid)" opacity="0.3"/>
                    
                    <!-- Line -->
                    <path d={chart.pathData} fill="none" stroke={chart.color} stroke-width="2"/>
                    
                    <!-- Points -->
                    {#each chart.points as point}
                      <circle cx={point.x} cy={point.y} r="3" fill={chart.color}/>
                      <text x={point.x} y={chart.height - 10} font-size="10" text-anchor="middle" fill="currentColor">{point.year}</text>
                    {/each}
                  </svg>
                </div>
              {:else}
                <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                  <div class="text-sm text-base-content/50">Fejl ved diagram</div>
                </div>
              {/if}
              <div class="text-xs text-base-content/50">
                Seneste: {formatNumber(data.kpi_trends.ghg_by_year[data.kpi_trends.ghg_by_year.length - 1]?.value || 0)} tCO₂e
              </div>
            {:else}
              <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                <div class="text-sm text-base-content/50">Utilstrækkelige data - kræver ≥2 årlige datapunkter</div>
              </div>
            {/if}
          </div>

          <!-- Energy Chart -->
          <div class="space-y-2">
            <h3 class="font-medium">Energiforbrug (MWh)</h3>
            {#if data.kpi_trends.energy_by_year.length >= 2}
              {@const chart = createLineChart(data.kpi_trends.energy_by_year, '#16a34a')}
              {#if chart && chart.pathData}
                <div class="h-48 bg-base-200 rounded p-2">
                  <svg viewBox="0 0 {chart.width} {chart.height}" class="w-full h-full">
                    <!-- Grid lines -->
                    <defs>
                      <pattern id="grid-energy" width="40" height="20" patternUnits="userSpaceOnUse">
                        <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#e5e7eb" stroke-width="0.5"/>
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid-energy)" opacity="0.3"/>
                    
                    <!-- Line -->
                    <path d={chart.pathData} fill="none" stroke={chart.color} stroke-width="2"/>
                    
                    <!-- Points -->
                    {#each chart.points as point}
                      <circle cx={point.x} cy={point.y} r="3" fill={chart.color}/>
                      <text x={point.x} y={chart.height - 10} font-size="10" text-anchor="middle" fill="currentColor">{point.year}</text>
                    {/each}
                  </svg>
                </div>
              {:else}
                <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                  <div class="text-sm text-base-content/50">Fejl ved diagram</div>
                </div>
              {/if}
              <div class="text-xs text-base-content/50">
                Seneste: {formatNumber(data.kpi_trends.energy_by_year[data.kpi_trends.energy_by_year.length - 1]?.value || 0)} MWh
              </div>
            {:else}
              <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                <div class="text-sm text-base-content/50">Utilstrækkelige data - kræver ≥2 årlige datapunkter</div>
              </div>
            {/if}
          </div>

          <!-- Waste Chart -->
          <div class="space-y-2">
            <h3 class="font-medium">Affald genereret (t)</h3>
            {#if data.kpi_trends.waste_by_year.length >= 2}
              {@const chart = createLineChart(data.kpi_trends.waste_by_year, '#f59e0b')}
              {#if chart && chart.pathData}
                <div class="h-48 bg-base-200 rounded p-2">
                  <svg viewBox="0 0 {chart.width} {chart.height}" class="w-full h-full">
                    <!-- Grid lines -->
                    <defs>
                      <pattern id="grid-waste" width="40" height="20" patternUnits="userSpaceOnUse">
                        <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#e5e7eb" stroke-width="0.5"/>
                      </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid-waste)" opacity="0.3"/>
                    
                    <!-- Line -->
                    <path d={chart.pathData} fill="none" stroke={chart.color} stroke-width="2"/>
                    
                    <!-- Points -->
                    {#each chart.points as point}
                      <circle cx={point.x} cy={point.y} r="3" fill={chart.color}/>
                      <text x={point.x} y={chart.height - 10} font-size="10" text-anchor="middle" fill="currentColor">{point.year}</text>
                    {/each}
                  </svg>
                </div>
              {:else}
                <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                  <div class="text-sm text-base-content/50">Fejl ved diagram</div>
                </div>
              {/if}
              <div class="text-xs text-base-content/50">
                Seneste: {formatNumber(data.kpi_trends.waste_by_year[data.kpi_trends.waste_by_year.length - 1]?.value || 0)} t
              </div>
            {:else}
              <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                <div class="text-sm text-base-content/50">Utilstrækkelige data - kræver ≥2 årlige datapunkter</div>
              </div>
            {/if}
          </div>
        </div>

        <!-- Optional Intensity Chart -->
        {#if data.kpi_trends.ghg_per_employee.length >= 2}
          {@const chart = createLineChart(data.kpi_trends.ghg_per_employee, '#8b5cf6')}
          <div class="mt-6 pt-6 border-t border-base-300">
            <h3 class="font-medium mb-2">Drivhusgasudledning pr. medarbejder (tCO₂e/medarbejder)</h3>
            {#if chart && chart.pathData}
              <div class="h-32 bg-base-200 rounded p-2">
                <svg viewBox="0 0 {chart.width} {chart.height}" class="w-full h-full">
                  <!-- Grid lines -->
                  <defs>
                    <pattern id="grid-intensity" width="40" height="20" patternUnits="userSpaceOnUse">
                      <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#e5e7eb" stroke-width="0.5"/>
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="url(#grid-intensity)" opacity="0.3"/>
                  
                  <!-- Line -->
                  <path d={chart.pathData} fill="none" stroke={chart.color} stroke-width="2"/>
                  
                  <!-- Points -->
                  {#each chart.points as point}
                    <circle cx={point.x} cy={point.y} r="2" fill={chart.color}/>
                    <text x={point.x} y={chart.height - 5} font-size="9" text-anchor="middle" fill="currentColor">{point.year}</text>
                  {/each}
                </svg>
              </div>
            {:else}
              <div class="h-32 bg-base-200 rounded p-4 flex items-center justify-center">
                <div class="text-sm text-base-content/50">Fejl ved diagram</div>
              </div>
            {/if}
            <div class="text-xs text-base-content/50 mt-1">
              Beregnet kun for år med medarbejderdata
            </div>
          </div>
        {/if}
      </div>

      <!-- Row 3: Quality Snapshot & Distribution -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Quality Snapshot -->
        <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
          <h2 class="text-xl font-semibold mb-4">Kvalitetsoverblik</h2>
          <div class="space-y-3">
            <!-- Units & Completeness Table -->
            <div class="overflow-x-auto">
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>KPI</th>
                    <th>Målenhed</th>
                    <th>Mest almindelig</th>
                    <th>Konsistens</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {#each Object.entries(data.quality_snapshot.units_analysis) as [kpi, analysis]}
                    <tr>
                      <td class="font-mono text-xs">{kpi}</td>
                      <td class="text-xs">{analysis.target_unit}</td>
                      <td class="text-xs">{analysis.most_common_unit}</td>
                      <td class="text-xs">{analysis.consistency_pct}%</td>
                      <td>
                        {#if analysis.status === 'OK'}
                          <span class="badge badge-success badge-xs">OK</span>
                        {:else if analysis.status === 'Mixed'}
                          <span class="badge badge-warning badge-xs">⚠️ Blandet</span>
                        {:else}
                          <span class="badge badge-ghost badge-xs">Ingen data</span>
                        {/if}
                      </td>
                    </tr>
                  {/each}
                  <tr class="border-t-2">
                    <td class="font-medium">Portefølje</td>
                    <td colspan="3" class="text-xs text-base-content/70">Samlet fuldstændighed</td>
                    <td class="font-bold">{data.quality_snapshot.portfolio_completeness.toFixed(1)}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Distribution Chart -->
        <div class="bg-base-100 rounded-lg p-6 shadow-sm border border-base-300">
          <h2 class="text-xl font-semibold mb-4">Fordeling</h2>
          {#if data.quality_snapshot.distribution_data}
            {@const histogram = createHistogram(data.quality_snapshot.distribution_data.values)}
            <div class="space-y-2">
              <h3 class="font-medium">Fordeling af samlet drivhusgasudledning ({data.quality_snapshot.distribution_data.year})</h3>
              {#if histogram && histogram.bars.length > 0}
                <div class="h-48 bg-base-200 rounded p-2">
                  <svg viewBox="0 0 {histogram.width} {histogram.height}" class="w-full h-full">
                    <!-- Histogram bars -->
                    {#each histogram.bars as bar}
                      <rect 
                        x={bar.x} 
                        y={bar.y} 
                        width={bar.width} 
                        height={bar.height} 
                        fill="#3b82f6" 
                        stroke="#1d4ed8" 
                        stroke-width="1"
                        opacity="0.8"
                      />
                      <!-- Count labels on bars -->
                      {#if bar.count > 0}
                        <text 
                          x={bar.x + bar.width / 2} 
                          y={bar.y - 5} 
                          font-size="10" 
                          text-anchor="middle" 
                          fill="currentColor"
                        >
                          {bar.count}
                        </text>
                      {/if}
                    {/each}
                  </svg>
                </div>
              {:else}
                <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
                  <div class="text-sm text-base-content/50">Fejl ved histogram</div>
                </div>
              {/if}
              <div class="text-xs text-base-content/50">
                {data.quality_snapshot.distribution_data.count} virksomheder, {histogram.binCount} intervaller
                · Seneste år med ≥5 virksomheder der rapporterer drivhusgasdata
              </div>
            </div>
          {:else}
            <div class="h-48 bg-base-200 rounded p-4 flex items-center justify-center">
              <div class="text-center">
                <div class="text-sm text-base-content/50">Utilstrækkelige data</div>
                <div class="text-xs text-base-content/40 mt-1">Kræver ≥5 virksomheder med drivhusgasdata</div>
              </div>
            </div>
          {/if}
        </div>
      </div>
    {:else if data && data.status_tiles && data.status_tiles.companies_count === 0}
      <!-- Empty Portfolio State -->
      <div class="text-center py-16">
        <div class="max-w-md mx-auto">
          <div class="text-6xl mb-4">📊</div>
          <h2 class="text-2xl font-semibold mb-2">Din portefølje er tom</h2>
          <p class="text-base-content/70 mb-6">
            Upload nogle validerede rapporter for at se indsigter om din porteføljes ESG-præstation.
          </p>
          <a href="/submit" class="btn btn-primary">
            Upload din første rapport
          </a>
        </div>
      </div>
    {:else}
      <div class="text-center py-12 text-base-content/50">
        Ingen indsigtsdata tilgængelige
      </div>
    {/if}
  </div>
</div>


