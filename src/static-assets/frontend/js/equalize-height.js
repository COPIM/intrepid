
$( document ).ready(function() {
   var max_height = 0
   $('.row-eq-height').each(function( index, element ){
      height = ( $( this ).height() );
      if (height > max_height) {
        max_height = height;
      }
  });

   $('.row-eq-height').height(max_height);
});
