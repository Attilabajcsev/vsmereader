<script lang="ts">
  import { goto } from '$app/navigation';
  let uploading: boolean = $state(false);
  let uploadError: string | null = $state(null);
  let showFallback: boolean = $state(false);
  let fallbackCompanyName: string = $state('');

  async function onSubmit(ev: Event) {
    ev.preventDefault();
    const formEl = ev.target as HTMLFormElement;
    const fileInput = formEl.querySelector('#ixbrl-file') as HTMLInputElement;
    if (!fileInput?.files || fileInput.files.length === 0) { 
      uploadError = 'Vælg venligst en fil'; 
      return; 
    }
    
    const formData = new FormData();
    formData.append('original_file', fileInput.files[0]);
    
    // Add company name if provided in fallback
    if (showFallback && fallbackCompanyName.trim()) {
      formData.append('company_name', fallbackCompanyName.trim());
    }
    
    uploadError = null;
    uploading = true;
    
    try {
      const res = await fetch('/api/reports/upload', { method: 'POST', body: formData, credentials: 'include' });
      if (!res.ok) {
        const text = await res.text();
        // Check if error suggests we need company info
        if (text.includes('company name') || text.includes('entity information')) {
          showFallback = true;
          uploadError = 'Kunne ikke udtrække virksomhedsoplysninger fra filen. Angiv venligst virksomhedsnavn nedenfor.';
        } else {
          uploadError = text || res.statusText;
        }
      } else {
        const data = await res.json();
        goto(`/reports/${data.id}`);
      }
    } catch (e) {
      uploadError = 'Upload fejlede';
    } finally {
      uploading = false;
    }
  }
</script>

<div class="min-h-screen bg-base-200/40 flex items-start justify-center pt-20 px-4">
  <div class="w-full max-w-2xl rounded-box border border-base-300 bg-base-100 p-6 shadow-md space-y-5">
    <h1 class="text-2xl font-semibold text-center">Indsend rapport</h1>
    <p class="text-center text-base-content/70">
      Upload din iXBRL vSME rapport
    </p>
    <form class="space-y-4" onsubmit={onSubmit}>
      {#if uploadError}
        <div class="alert alert-error"><span>{uploadError}</span></div>
      {/if}
      <div class="form-control">
        <div class="mb-1 text-sm font-medium">iXBRL fil (.xhtml, .html eller .zip)</div>
        <input id="ixbrl-file" class="file-input file-input-bordered w-full" type="file" accept=".xhtml,.html,.zip" />
      </div>
      
      {#if showFallback}
        <div class="form-control">
          <div class="mb-1 text-sm font-medium">Virksomhedsnavn</div>
          <input 
            bind:value={fallbackCompanyName} 
            class="input input-bordered w-full" 
            type="text" 
            placeholder="Indtast virksomhedsnavn" 
            required={showFallback}
          />
          <div class="text-xs text-base-content/60 mt-1">
            Vi kunne ikke udtrække virksomhedsnavnet fra din fil automatisk.
          </div>
        </div>
      {/if}
      
      <div class="pt-2">
        <button class="btn btn-primary w-full sm:w-auto" type="submit" disabled={uploading}>
          {#if uploading}
            <span class="loading loading-spinner loading-sm"></span> Behandler…
          {:else}
            Indsend
          {/if}
        </button>
      </div>
    </form>
  </div>
</div>


