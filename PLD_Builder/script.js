jQuery(function($) {
	update_tz();
	filter_requesters();

	// setup relative time display
	function update_tz() {
		$('time.timeago').timeago();
	}

	// draw filter for requesters
	function filter_requesters() {
		var requesters = ['everyone'];
		$('div b.requester').each(function(i, d) {
			var requester = $(d).text();
			if (!~requesters.indexOf(requester)) {
				requesters.push(requester);
			}
		});

		var $filter = $('#requesters-filter');
		if ($filter.length == 0) {
			$filter = $('<div id=requesters-filter>Filter by requesters:<br></div>');
			$('body').prepend($filter);
		}
		requesters.forEach(function(r) {
			var $button = $('<button class=request-filter>'+ r + '</button>');
			$button.on('click', function() {
				$('div#requesters-filter button').removeAttr('disabled');
				$('div.request').filter(function(i, d) {
					var c = $(d).find('b.requester').text();
					if (c == r || r == 'everyone') {
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
