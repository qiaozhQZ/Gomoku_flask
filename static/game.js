$.ajaxSetup({
    type: 'POST',
    timeout: 30000, // set default timeout to 15 sec.
    error: function(request, status, err) {
        if (status == "timeout") {
            // timeout -> reload the page and try again
            console.log("timeout");
        } else {
            // another error occured
            alert("error: " + request + status + err);
        }
        window.location.reload();
    }
})

let clickable = false;
let num_games_left = 99999;

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
    $('.move_location').click(click_handler);
}

function disable_clicking(){
    clickable = false;
    $('.move_location').removeClass('make_clickable');
    $('#hint_button').attr('disabled','disabled');
    $('.move_location').off('click', click_handler);
}

function make_ai_move(){
    if (move_color == 'white') {
        disable_clicking();
        $.post('get_ai_move').done(function(data){
            console.log('opponent move:');
            console.log(data);
            hideLoader();
            $('#loc'+data['location']).removeClass('move_location');
            $('#loc'+data['location']).addClass(move_color + 'stone');
            flip_color();

            $.post('move/' + data['i'] + '/' + data['j'])
                .done(function(data){
                    $(document).trigger('move_complete', data);
                    console.log('opp move done');
                    console.log(data);
                    enable_clicking();
                    if (data['end']){
                        display_winner(data['winner']);
                    }
                });
        });
    }

    else {
        enable_clicking()
    }

}

function click_handler(e){
    if (clickable){
        showLoader();
        $('.hintstone').removeClass('hintstone');

        let square = this;
        let row = $(square).attr('data-row');
        let col = $(square).attr('data-col');
        disable_clicking();

        $('#score').html('--');
        $(square).off('click')
        $(square).removeClass('move_location');
        $(square).addClass(move_color + 'stone');


        flip_color();

        $.post('move/' + row + '/' + col)
            .done(function(data){
                $(document).trigger('move_complete', data);
                console.log('your move:');
                console.log(data);
                $('#score').html(data['score']);

                if (data['end']){
                    display_winner(data['winner']);
                }
                else{
                    make_ai_move();
                }
            });
    }
}

function display_winner(winner){
    $(document).trigger('game_end');
    disable_clicking();
    $('#toolbar').hide();
    $('#start_instructions').hide();
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
    num_games_left -= 1; //count down the games left

    if (num_games_left < 1) { //advance to survey if no games left
        $.ajax({
            type: "POST",
            url: '/advance_stage',
            data: JSON.stringify({'page':'testing'}),
            contentType: "application/json",
            dataType: 'json',
            success: function(resp) {
                $('#new_game_button').hide();
                $('#next_button').click(function() {
                    window.location.href = resp['next_page'];
                });
                $('#next_button').show();
            },
        });
    }
}

function clear_board(){
    $('.blackstone').addClass('move_location').addClass('make_clickable').removeClass('blackstone');
    $('.whitestone').addClass('move_location').addClass('make_clickable').removeClass('whitestone');
    $('.hintstone').removeClass('hintstone');
    move_color = "black";
}


// Function to show the loader
function showLoader() {
    document.getElementById('ai-loader').style.display = 'block';
}

// Function to hide the loader
function hideLoader() {
    document.getElementById('ai-loader').style.display = 'none';
}

$().ready(function(){
    hideLoader();
    window.addEventListener( "pageshow", function ( event ) {
        var historyTraversal = event.persisted ||
            ( typeof window.performance != "undefined" &&
                window.performance.getEntriesByType("navigation")[0].type === "back_forward"
            );
        if ( historyTraversal ) {
            // Handle page restore.
            window.location.reload();
        }
    });

    // $('#next_button').hide();

    $('#hint_button').click(function(e){
        if (clickable){
            disable_clicking();
            $('.hintstone').removeClass('hintstone');
            $.post('get_hint').done(function(data){
                $('#loc'+data['location']).addClass('hintstone');
                enable_clicking();
                $.ajax({
                    type: "POST",
                    url: '/log',
                    data: JSON.stringify({'event':'hint', 'location': data['location']}),
                    contentType: "application/json",
                    dataType: 'json',
                    success: function(resp) {},
                });
            });
        }
    });

    $('#new_game_button').click(function(){
        move_color = 'black';
        $.ajax({
            type: "POST",
            url: '/new_game',
            data: JSON.stringify({}),
            contentType: "application/json",
            dataType: 'json',
            success: function(resp) {
                $(document).trigger('new_game');
                hideLoader();
                clear_board();
                $('#toolbar').show();
                $('#winning_dialog').hide();
                $('#start_instructions').show();
                enable_clicking();
                $('#score').html('--');
            },
        });

        $.ajax({
            type: "POST",
            url: '/log',
            data: JSON.stringify({'event':'new_game'}),
            contentType: "application/json",
            dataType: 'json',
            success: function(resp) {},
        });
    });

    enable_clicking();


});
