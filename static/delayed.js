function disable_review(){
    console.log('disable?');
    $('#review').hide()
}

function enable_review(){
    $('#review').show()
}

$().ready(function(){

    disable_review();

    function prev_move(){
        if (current_idx >= 0){
            $('.hintstone').removeClass('hintstone');	
            $('#loc' + move_seq[current_idx]).removeClass(color_seq[current_idx] + "stone");
            current_idx -= 1;

            if (current_idx >= 0){
                $('#score').html(score_seq[current_idx]);
            }
            else{
                $('#score').html('--');
            }

            $.ajax({
                    type: "POST",
                    url: '/log',
                    data: JSON.stringify({'event':'previous'}),
                    contentType: "application/json",
                    dataType: 'json',
                    success: function(resp) {},
            });
        }
    }

    function next_move(){
        if (current_idx < move_seq.length - 1){
            $('.hintstone').removeClass('hintstone');	
            current_idx += 1;
            $('#loc' + move_seq[current_idx]).addClass(color_seq[current_idx] + "stone");
            $('#score').html(score_seq[current_idx]);

            $.ajax({
                    type: "POST",
                    url: '/log',
                    data: JSON.stringify({'event':'next'}),
                    contentType: "application/json",
                    dataType: 'json',
                    success: function(resp) {},
            });
        }
    }
    
    $('#previous').click(function(){
        prev_move();
    });

    $('#next').click(function(){
        next_move();
    });

    $('#hint').click(function(){
        if (current_idx < move_seq.length - 1){
            $('.hintstone').removeClass('hintstone');	
            $('#loc'+hint_seq[current_idx+1]).addClass('hintstone');	
            $.ajax({
                    type: "POST",
                    url: '/log',
                    data: JSON.stringify({'event':'hint', 'location': hint_seq[current_idx+1]}),
                    contentType: "application/json",
                    dataType: 'json',
                    success: function(resp) {},
            });
        }
    });

    //TODO, not working
    $('#end_game').click(function(){
        enable_review();
    });

    $(document).on("new_game", function() {
        disable_review();
        move_seq = [];
        color_seq = [];
        score_seq = [];
        hint_seq = [];
        current_idx = -1;
    });

    $(document).on("game_end", function() {
        enable_review();
    });

    $(document).on("move_complete", function(ev, data){
        move_seq.push(data['move']);
        color_seq.push(data['color']);
        score_seq.push(data['score']);
        hint_seq.push(data['hint']);
        current_idx += 1;
    });

});
