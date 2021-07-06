let clickable = false;


$().ready(function(){
	enable_clicking();

	$('.move_location').click(function(e){
		if (clickable){
			disable_clicking();
			$('.hintstone').removeClass('hintstone');	

			let square = this;
			let row = $(square).attr('data-row');
			let col = $(square).attr('data-col');

			$('#score').html('--');
			$(square).removeClass('move_location');	
			$(square).addClass(move_color + 'stone');	

			flip_color();

			$.post('move/' + row + '/' + col)
				.done(function(data){
					console.log('your move:');
					console.log(data);
					$('#score').html(data['score']);

					if (data['end']){
						display_winner(data['winner']);
					}
					else{
						$.post('optimal_move').done(function(data){
							console.log('opponent move:');
							console.log(data);
							$('#loc'+data['location']).removeClass('move_location');	
							$('#loc'+data['location']).addClass(move_color + 'stone');	
							flip_color()

							$.post('move/' + data['i'] + '/' + data['j'])
								.done(function(data){
									console.log('opp move done');
									console.log(data);
									enable_clicking();
									if (data['end']){
										display_winner(data['winner']);
									}
								});
						});
					}
				});
		}
	});

	$('#hint_button').click(function(e){
		if (clickable){
			disable_clicking();
			$('.hintstone').removeClass('hintstone');	
			$.post('optimal_move').done(function(data){
				$('#loc'+data['location']).addClass('hintstone');	
				enable_clicking();
			});
		}
	});

	$('#new_game_button').click(function(){
		clear_board();
		$('#toolbar').show();
		$('#winning_dialog').hide();
		enable_clicking();
	});

	function display_winner(winner){
		disable_clicking();
		$('#toolbar').hide();
		$('#winning_dialog').show();
		if (winner == 1){
			$('#winning_text').text('You Won!');
		} 
		else if (winner == 2){
			$('#winning_text').text('You Lost!');
		}
		else{
			$('#winning_text').text('Draw Game!');
		}
	}

	function flip_color(){
		if (move_color == 'black'){
			move_color = 'white';
		}
		else{
			move_color = 'black';
		}
	}

	function enable_clicking(){
		clickable = true;
		$('.move_location').addClass('make_clickable');
		$('#hint_button').removeAttr('disabled');
	}

	function disable_clicking(){
		clickable = false;
		$('.move_location').removeClass('make_clickable');
		$('#hint_button').attr('disabled','disabled');
	}

	function clear_board(){
		$('.blackstone').addClass('make_location').addClass('make_clickable').removeClass('blackstone');
		$('.whitestone').addClass('make_location').addClass('make_clickable').removeClass('whitestone');
		$('.hintstone').removeClass('hintstone');
	}

	if (move_color == "white"){
		disable_clicking();
		$.post('optimal_move').done(function(data){
			console.log('opponent move:');
			console.log(data);
			$('#loc'+data['location']).removeClass('move_location');	
			$('#loc'+data['location']).addClass(move_color + 'stone');	
			flip_color()

			$.post('move/' + data['i'] + '/' + data['j']).done(function(data){
				console.log('opp move done');
				console.log(data);
				enable_clicking();
				if (data['end']){
					display_winner(data['winner']);
				}
			});
		});
	}

});
