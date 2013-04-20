jQuery(function($) {
	update_tz();

	// update date stamps to reflect viewers timezone
	function update_tz() {
		$('span#tz').each(function(i, el) {
			var $el = $(el);
			dt = new Date($el.text()).toString();
			// strip timezone name, it is usually wrong when not initialized
			// from TZ env, but reverse calculated from os data
			dt = dt.replace(/\s+\(.+\)/, "");
			// strip "GMT"
			dt = dt.replace(/GMT/, "");
			$el.text(dt);
		});
	}
});
