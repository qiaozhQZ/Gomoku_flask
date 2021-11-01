$().ready(function(){
	$.ajax({
		type: "GET",
		url: '/testing_games_left',
		data: '{}',
		contentType: 'application/json',
		dataType: 'json',
		success: function(games_left) {
			console.log(games_left);
			num_games_left = games_left['games'];
		},
	});
});
