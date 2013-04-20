jQuery(function($) {
	update_tz();
	filter_requesters();

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

	// draw filter for requesters
	function filter_requesters() {
		var requesters = [];
		$('div b.requester').each(function(i, d) {
			var requester = $(d).text();
			if (!~requesters.indexOf(requester)) {
				requesters.push(requester);
			}
		});

		var $filter = $('<div id=requesters-filter>Filter by requesters:<br></div>');
		$('body').prepend($filter);
		requesters.forEach(function(r) {
			var $button = $('<button class=request-filter>'+ r + '</button>');
			$button.on('click', function() {
				$('div#requesters-filter button').removeAttr('disabled');
				$('div.request').filter(function(i, d) {
					var c = $(d).find('b.requester').text();
					if (c == r) {
						$(d).show();
						$button.attr('disabled', 'disabled');
					} else {
						$(d).hide();
					}
				})
			})
			$filter.append($button);
		});
	}
});
