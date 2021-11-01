$().ready(function(){
	$.ajax({
		type: "GET",
		url: '/testing_games_left',
		data: '{}', //should be empty here
		contentType: 'application/json',
		dataType: 'json',
		success: function(games_left) {
			console.log(games_left);
			num_games_left = games_left['games'];
		},
	});
});
// need to add a query to advance_stage