<style lang="scss">
	@import "uview-plus/index.scss";

	page{
		background-color: rgb(249,250,251) !important;
	}
</style>
<script>
	import { checkWxVersionUpdate } from '@/utils/versionUpdate';
	export default {
		onLaunch: function() {
			checkWxVersionUpdate(true);
		},
		onShow: function() {
			console.log('App Show')
		},
		onHide: function() {
			console.log('App Hide')
		}
	}
</script>