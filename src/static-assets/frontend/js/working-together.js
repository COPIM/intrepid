let current_swipe = 1;
let touchstartX = 0
let touchendX = 0
var handled = false;

$( document ).ready(function() {
  $('.working-together-info').hide();
  $('.working-together-info-1').show();

  $('.working-together-mobile-block').hide();
  $('.working-together-mobile-block-1').show();

  // on mobile, bind for swiping
  $( ".working-together-mobile").on('touchstart', e => { touchstartX = e.changedTouches[0].screenX });

  $( ".dot").on('click', e => { 
    the_object = $('#' + e.target.id);
    handleDot(e.target.id);
  });
  

  $( ".working-together-mobile").on('touchend', e => { 
    e.stopImmediatePropagation();

    // ensure the events don't fire multiple times
    if(e.type == "touchend") {
        handled = true;
        touchendX = e.changedTouches[0].screenX;
        handleGesture();
    }
    else if(e.type == "click" && !handled) {

      // get the final target
      if (e.target.id) {
        the_object = $('#' + e.target.id);

        if ($('#' + e.target.id).hasClass('dot')){
          handleDot(e.target.id);
        } else {

        }
      }
    }
    else {
        handled = false;
    }
  });
  

});

function handleGesture() {
  if (touchendX < touchstartX) incrementSlider();
  if (touchendX > touchstartX) decrementSlider();
}

function incrementSlider() {
  if (current_swipe < 4) {
    
    current_swipe = current_swipe + 1;

    handleDot(current_swipe);
  }
}

function decrementSlider() {
  if (current_swipe > 1) {
    
    current_swipe = current_swipe - 1;

    handleDot(current_swipe);
  }
}

function handleDot(dot_id) {
  // set the swipe index if we are given a string
  if (typeof dot_id === 'string' || dot_id instanceof String) {
    // get the number from the dot ID
    dot_id = dot_id[4];
    current_swipe = parseInt(dot_id);
  }

  // change the dots
  $('.dot').removeClass('active');
  $('#dot-' + current_swipe).addClass('active');

  // show the right div
  $('.working-together-mobile-block').hide();
  $('.working-together-mobile-block-' + current_swipe).show();
}


$(document).on('click', '.first-pill', function() {
  // hide all existing divs
  $('.working-together-info').hide(1000);

  // lookup the div to show: it's the 17th character in the ID of the calling button
  var info_number = $(this).attr('id')[17];

  // build a class name to show
  var class_name = ".working-together-info-" + info_number;

  $(class_name).show(4000);

  // now change the selected item
  $('.mid-pill').addClass('inactive-pill');
  $('.first-pill').addClass('inactive-pill');
  $(this).removeClass('inactive-pill');
  $(this).addClass('active-pill');
});

$(document).on('click', '.mid-pill', function() {
  // hide all existing divs
  $('.working-together-info').hide();

  // lookup the div to show: it's the 17th character in the ID of the calling button
  var info_number = $(this).attr('id')[17];

  // build a class name to show
  var class_name = ".working-together-info-" + info_number;

  $(class_name).show(4000);

  // now change the selected item
  $('.mid-pill').addClass('inactive-pill');
  $('.first-pill').addClass('inactive-pill');
  $(this).removeClass('inactive-pill');
  $(this).addClass('active-pill');
  
});
