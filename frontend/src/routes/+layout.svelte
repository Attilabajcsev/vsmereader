<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	let { data, children } = $props();
	let nonProtectedRoutes: string[] = ['/', '/login', '/register', '/login-oauth', '/oauth-google'];
</script>

<div class="flex min-h-screen flex-col">
	<!-- CVR-like ribbon: taller, segmented, login area highlighted -->
	<div class="bg-base-100/95 border-b border-base-300 shadow-sm">
		<div class="w-full">
			<div class="flex items-stretch">
				<!-- Left section: brand -->
				<div class="px-4 py-6 flex items-center">
					<a class="text-xl font-semibold select-none">IXBRL VSME Reader</a>
				</div>
				<!-- Divider -->
				<div class="w-px bg-base-300/80 my-2"></div>
				<!-- Middle section: nav links -->
				<div class="flex items-center px-1">
					{#if data.authed}
						<a class="px-4 py-6 hover:bg-base-200/60" href="/submit">Submit report</a>
						<div class="w-px bg-base-300/80 my-2"></div>
						<a class="px-4 py-6 hover:bg-base-200/60" href="/portfolio">Portfolio</a>
						<div class="w-px bg-base-300/80 my-2"></div>
						<a class="px-4 py-6 hover:bg-base-200/60" href="/insights">Insights</a>
					{/if}
				</div>
				<!-- Spacer -->
				<div class="flex-1"></div>
				<!-- Right section: login area with blue background -->
				<div class="flex items-stretch">
					{#if data.authed}
						<a class="px-6 py-6 bg-primary text-primary-content hover:opacity-90" href="/logout" data-sveltekit-preload-data="off">Logout</a>
					{:else}
						<a class="px-6 py-6 bg-primary text-primary-content hover:opacity-90" href="/login">Login</a>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<div class="flex-1">
		{@render children()}
	</div>

	<footer class="footer sm:footer-horizontal footer-center bg-base-300/70 text-base-content p-4">
		<aside>
			<p>Copyright © {new Date().getFullYear()} - IXBRL VSME Reader</p>
		</aside>
	</footer>
</div>
