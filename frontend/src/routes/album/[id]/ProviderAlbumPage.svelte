<script lang="ts">
	import { goto } from '$app/navigation';
	import { integrationStore } from '$lib/stores/integration';
	import BackButton from '$lib/components/BackButton.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import LastFmAlbumEnrichmentComponent from '$lib/components/LastFmAlbumEnrichment.svelte';
	import DeleteAlbumModal from '$lib/components/DeleteAlbumModal.svelte';
	import AddToPlaylistModal from '$lib/components/AddToPlaylistModal.svelte';
	import { createAlbumPageState } from './albumPageState.svelte';
	import AlbumHeader from './AlbumHeader.svelte';
	import UnmatchedFilesSection from './UnmatchedFilesSection.svelte';
	import { authStore } from '$lib/stores/authStore.svelte';
	import AlbumSourceBars from './AlbumSourceBars.svelte';
	import AlbumTrackList from './AlbumTrackList.svelte';
	import AlbumDiscovery from './AlbumDiscovery.svelte';
	import WhereToBuy from './WhereToBuy.svelte';
	import { albumHref } from '$lib/utils/entityRoutes';
	import LibraryAlbumCard from '$lib/components/library/LibraryAlbumCard.svelte';
	import { getLibraryAlbumCopiesQuery } from '$lib/queries/library/LibraryQueries.svelte';

	interface Props {
		data: { albumId: string };
	}

	let { data }: Props = $props();

	const pageState = createAlbumPageState(() => data.albumId);
	const localCopiesQuery = getLibraryAlbumCopiesQuery(() => data.albumId);
	const localCopies = $derived(localCopiesQuery.data?.items ?? []);
	let copyDialog: HTMLDialogElement;
	let mergeSourceId = $state<string | null>(null);
	let mergeTargetId = $state<string | null>(null);

	function showCopies(): void {
		mergeSourceId = null;
		mergeTargetId = null;
		copyDialog.showModal();
	}

	function startMerge(): void {
		if (!mergeSourceId || !mergeTargetId || mergeSourceId === mergeTargetId) return;
		copyDialog.close();
		void goto(`${albumHref(mergeSourceId)}?mergeTarget=${encodeURIComponent(mergeTargetId)}`);
	}

	$effect(() => {
		const canonicalId = pageState.album?.musicbrainz_id;
		if (canonicalId && canonicalId !== data.albumId) {
			void goto(albumHref(canonicalId), { replaceState: true });
		}
	});
</script>

<div class="w-full px-2 sm:px-4 lg:px-8 py-4 sm:py-8 max-w-7xl mx-auto">
	<div class="mb-4">
		<BackButton />
	</div>

	{#if pageState.error}
		<div class="flex items-center justify-center min-h-[50vh]">
			<div class="alert alert-error">
				<span>{pageState.error}</span>
			</div>
		</div>
	{:else if pageState.loadingBasic || !pageState.album}
		<div class="space-y-6 sm:space-y-8">
			<div class="flex flex-col lg:flex-row gap-6 lg:gap-8">
				<div class="skeleton w-full lg:w-64 xl:w-80 aspect-square rounded-box shrink-0"></div>
				<div class="flex-1 flex flex-col justify-end space-y-4">
					<div class="skeleton h-4 w-20"></div>
					<div class="skeleton h-12 w-3/4"></div>
					<div class="skeleton h-6 w-1/2"></div>
					<div class="flex gap-4 mt-6">
						<div class="skeleton h-12 w-32"></div>
						<div class="skeleton h-12 w-32"></div>
					</div>
				</div>
			</div>

			<div class="space-y-2">
				<div class="skeleton h-8 w-32 mb-4"></div>
				{#each Array(8) as _, i (`skeleton-${i}`)}
					<div class="skeleton h-12 w-full"></div>
				{/each}
			</div>
		</div>
	{:else if pageState.album}
		{@const album = pageState.album}
		<div class="space-y-6 sm:space-y-8">
			<AlbumHeader
				{album}
				tracksInfo={pageState.tracksInfo}
				loadingTracks={pageState.loadingTracks}
				inLibrary={pageState.inLibrary}
				isRequested={pageState.isRequested}
				requesting={pageState.requesting}
				refreshing={pageState.refreshing}
				headerDownloadTask={pageState.headerDownloadTask}
				managementHeld={pageState.headerManagementHeld}
				downloadClientConfigured={$integrationStore.download_client}
				libraryInLibrary={pageState.libraryInLibrary}
				libraryTrackCount={pageState.libraryTrackCount}
				libraryBelowCutoff={pageState.libraryBelowCutoff}
				coverageExpected={pageState.coverageExpected}
				coverageCovered={pageState.coverageCovered}
				mbTrackCount={pageState.tracksInfo?.total_tracks ?? 0}
				releaseGroupMbid={album.musicbrainz_id}
				{localCopies}
				onrequest={pageState.handleRequest}
				ondelete={pageState.handleDeleteClick}
				onrefresh={pageState.refreshAll}
				onartistclick={pageState.goToArtist}
				onmergecopies={showCopies}
			/>

			{#if localCopies.length > 1}
				<section
					class="rounded-box border border-base-content/10 bg-base-200/35 p-4 sm:p-5"
					aria-labelledby="owned-copies-title"
				>
					<h2 id="owned-copies-title" class="text-lg font-bold">Copies in your library</h2>
					<p class="mt-1 max-w-2xl text-sm text-base-content/55">
						This MusicBrainz release matches more than one local album. Choose the copies you want to
						combine.
					</p>
					<div class="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
						{#each localCopies as localCopy (localCopy.id)}
							<LibraryAlbumCard album={localCopy} />
						{/each}
					</div>
				</section>
			{/if}

			<WhereToBuy releaseGroupMbid={album.musicbrainz_id} enabled={!pageState.loadingTracks} />

			{#if pageState.loadingTracks}
				<div class="space-y-3">
					<h2 class="text-xl sm:text-2xl font-bold">Tracks</h2>
					<div class="bg-base-200 rounded-box overflow-hidden">
						<ul class="list">
							{#each Array(8) as _, i (`track-skeleton-${i}`)}
								<li class="list-row p-3 sm:p-4">
									<div class="flex items-center gap-4 w-full">
										<div class="skeleton w-8 h-4"></div>
										<div class="skeleton flex-1 h-4"></div>
										<div class="skeleton w-12 h-4"></div>
									</div>
								</li>
							{/each}
						</ul>
					</div>
				</div>
			{:else if pageState.tracksInfo && pageState.tracksInfo.tracks.length > 0}
				<div class="space-y-3">
					<div class="flex items-center justify-between flex-wrap gap-2">
						<h2 class="text-xl sm:text-2xl font-bold">Tracks</h2>
						{#if pageState.quota}
							<div class="flex items-center gap-2">
								<progress
									class="progress progress-accent w-20 h-1.5"
									value={pageState.quota.used}
									max={pageState.quota.limit}
								></progress>
								<span class="text-xs opacity-60">{pageState.quota.remaining}/{pageState.quota.limit}</span>
							</div>
						{/if}
					</div>

					<AlbumSourceBars
						{album}
						tracksInfo={pageState.tracksInfo}
						trackLinks={pageState.trackLinks}
						albumLink={pageState.albumLink}
						jellyfinMatch={pageState.jellyfinMatch}
						localMatch={pageState.localMatchForPlayback}
						navidromeMatch={pageState.navidromeMatch}
						plexMatch={pageState.plexMatch}
						loadingJellyfin={pageState.loadingJellyfin}
						loadingLocal={pageState.loadingLocal}
						loadingNavidrome={pageState.loadingNavidrome}
						loadingPlex={pageState.loadingPlex}
						youtubeEnabled={$integrationStore.youtube}
						youtubeApiConfigured={$integrationStore.youtube_api}
						jellyfinEnabled={$integrationStore.jellyfin}
						localfilesEnabled={$integrationStore.localfiles}
						navidromeEnabled={$integrationStore.navidrome}
						plexEnabled={$integrationStore.plex}
						jellyfinCallbacks={pageState.jellyfinCallbacks}
						localCallbacks={pageState.localCallbacks}
						localDownloadCallback={pageState.localDownloadCallback}
						navidromeCallbacks={pageState.navidromeCallbacks}
						plexCallbacks={pageState.plexCallbacks}
						onTrackLinksUpdate={pageState.handleTrackLinksUpdate}
						onAlbumLinkUpdate={pageState.handleAlbumLinkUpdate}
						onQuotaUpdate={pageState.handleQuotaUpdate}
					/>

					<AlbumTrackList
						{album}
					renderedTrackSections={pageState.renderedTrackSections}
						trackLinkMap={pageState.trackLinkMap}
						jellyfinMatch={pageState.jellyfinMatch}
						localMatch={pageState.localMatch}
						navidromeMatch={pageState.navidromeMatch}
						plexMatch={pageState.plexMatch}
						jellyfinTrackMap={pageState.jellyfinTrackMap}
						localTrackMap={pageState.localTrackMap}
						navidromeTrackMap={pageState.navidromeTrackMap}
						plexTrackMap={pageState.plexTrackMap}
						jellyfinTracks={pageState.jellyfinTracks}
						localTracks={pageState.localTracks}
						navidromeTracks={pageState.navidromeTracks}
						plexTracks={pageState.plexTracks}
						trackLinks={pageState.trackLinks}
						youtubeEnabled={$integrationStore.youtube}
						youtubeApiConfigured={$integrationStore.youtube_api}
						jellyfinEnabled={$integrationStore.jellyfin}
						localfilesEnabled={$integrationStore.localfiles}
						navidromeEnabled={$integrationStore.navidrome}
						plexEnabled={$integrationStore.plex}
						libraryTracksByRecording={pageState.libraryTracksByRecording}
						libraryTracksByPosition={pageState.libraryTracksByPosition}
						heldByRecording={pageState.heldByRecording}
						heldByPosition={pageState.heldByPosition}
						trackDownloadTasks={pageState.trackDownloadTasks}
						releaseGroupMbid={album.musicbrainz_id}
						onPlaySourceTrack={pageState.playSourceTrack}
						onTrackGenerated={pageState.handleTrackGenerated}
						onQuotaUpdate={pageState.handleQuotaUpdate}
						getTrackContextMenuItems={pageState.getTrackContextMenuItems}
					/>

					<UnmatchedFilesSection
						orphans={pageState.libraryOrphans}
						albumMbid={album.musicbrainz_id}
						canRemove={authStore.isTrusted}
					/>

					<AddToPlaylistModal bind:this={pageState.playlistModalRef} />
				</div>
			{:else if pageState.tracksError}
				<div class="space-y-3">
					<h2 class="text-xl sm:text-2xl font-bold">Tracks</h2>
					<div class="alert alert-warning">
						<span>Couldn't load the track list.</span>
						<button class="btn btn-sm btn-ghost" onclick={pageState.retryTracks}> Retry </button>
					</div>
				</div>
			{:else}
				<div class="space-y-3">
					<h2 class="text-xl sm:text-2xl font-bold">Tracks</h2>
					<div class="alert alert-warning">
						<span>No tracks available.</span>
						<button class="btn btn-sm btn-ghost" onclick={pageState.retryTracks}> Retry </button>
					</div>
				</div>
			{/if}

			{#if album.release_date}
				<div class="text-xs opacity-60">
					<span class="font-semibold">Release Date:</span>
					{album.release_date}
				</div>
			{/if}

			{#if pageState.loadingLastfm || pageState.lastfmEnrichment}
				<LastFmAlbumEnrichmentComponent
					enrichment={pageState.lastfmEnrichment}
					loading={pageState.loadingLastfm}
				/>
			{/if}

			<AlbumDiscovery
				moreByArtist={pageState.moreByArtist}
				similarAlbums={pageState.similarAlbums}
				loadingDiscovery={pageState.loadingDiscovery}
				artistName={album.artist_name}
			/>
		</div>
	{:else}
		<div class="flex items-center justify-center min-h-[50vh]">
			<p class="text-base-content/60">Album not found</p>
		</div>
	{/if}
</div>

<dialog bind:this={copyDialog} class="modal" aria-labelledby="combine-copies-title">
	<div class="modal-box max-w-2xl">
		<h2 id="combine-copies-title" class="text-xl font-bold">Combine local album copies</h2>
		<p class="mt-1 text-sm text-base-content/60">
			Choose the source copy whose tracks will be combined and the destination copy to keep.
			You will select the MusicBrainz edition afterward.
		</p>
		<div class="mt-5 grid gap-3 sm:grid-cols-2">
			{#each localCopies as localCopy (localCopy.id)}
				<label
					class="flex cursor-pointer items-start gap-3 rounded-box border border-base-content/10 p-3 hover:border-primary/50"
				>
					<input
						type="radio"
						name="merge-source"
						class="radio radio-primary mt-1"
						checked={mergeSourceId === localCopy.id}
						onchange={() => (mergeSourceId = localCopy.id)}
					/>
					<span class="min-w-0">
						<span class="block font-medium">Source: {localCopy.title}</span>
						<span class="block text-xs text-base-content/55">{localCopy.track_count} tracks</span>
					</span>
				</label>
			{/each}
		</div>
		<div class="mt-4 grid gap-3 sm:grid-cols-2">
			{#each localCopies as localCopy (localCopy.id)}
				<label
					class="flex cursor-pointer items-start gap-3 rounded-box border border-base-content/10 p-3 hover:border-primary/50"
				>
					<input
						type="radio"
						name="merge-target"
						class="radio radio-primary mt-1"
						checked={mergeTargetId === localCopy.id}
						onchange={() => (mergeTargetId = localCopy.id)}
					/>
					<span class="min-w-0">
						<span class="block font-medium">Keep: {localCopy.title}</span>
						<span class="block text-xs text-base-content/55">{localCopy.track_count} tracks</span>
					</span>
				</label>
			{/each}
		</div>
		<div class="modal-action">
			<button type="button" class="btn btn-ghost" onclick={() => copyDialog.close()}>Cancel</button>
			<button
				type="button"
				class="btn btn-primary"
				disabled={!mergeSourceId || !mergeTargetId || mergeSourceId === mergeTargetId}
				onclick={startMerge}>Continue to edition selection</button
			>
		</div>
	</div>
</dialog>

<Toast bind:show={pageState.showToast} message={pageState.toastMessage} type={pageState.toastType} />

{#if pageState.showDeleteModal && pageState.album}
	<DeleteAlbumModal
		albumTitle={pageState.album.title}
		artistName={pageState.album.artist_name}
		musicbrainzId={pageState.album.musicbrainz_id}
		ondeleted={pageState.handleDeleted}
		onclose={() => {
			pageState.showDeleteModal = false;
		}}
	/>
{/if}
