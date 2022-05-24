function disable_review(){
    console.log('disable?');
    $('#previous').hide()
    $('#hint').hide()
    $('#next').hide()
    $('.score_div').hide()
    $('.comment_div').hide()
}

function enable_review(){
    $('#previous').show()
    $('#hint').show()
    $('#next').show()
    $('.score_div').show()
    $('.comment_div').show()
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
        }
    }

    function next_move(){
        if (current_idx < move_seq.length - 1){
            $('.hintstone').removeClass('hintstone');	
            current_idx += 1;
            $('#loc' + move_seq[current_idx]).addClass(color_seq[current_idx] + "stone");
            $('#score').html(score_seq[current_idx]);
        }
    }
    
    $('#previous').click(function(){
        prev_move();
        /*
        while (color_seq[current_idx] != "white" && current_idx > 0){
            prev_move();
        }
        */
    });

    $('#next').click(function(){
        next_move();
        /*
        while (color_seq[current_idx] != "white" && current_idx < move_seq.length - 1){
            next_move();
        }
        */
    });

    $('#hint').click(function(){
        console.log('beep')
        if (current_idx < move_seq.length - 1){
            $('.hintstone').removeClass('hintstone');	
            $('#loc'+hint_seq[current_idx+1]).addClass('hintstone');	
        }
    });

    $(document).on("game_end", function() {
        console.log('triggered!');
        enable_review();
    });

});
