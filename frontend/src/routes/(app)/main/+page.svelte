<script lang="ts">
    import { redirect } from '@sveltejs/kit';
    import { goto } from '$app/navigation';
    $effect(() => { goto('/portfolio'); });
    // Legacy page removed; redirect to portfolio
</script>

<div class="p-6">Redirecting to Portfolio… <a class="link" href="/portfolio">Go now</a></div>
