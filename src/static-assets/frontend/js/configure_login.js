
$( document ).ready(function() {
    $('#id_auth-username').attr('placeholder','Username');
    $('#id_auth-password').attr('placeholder','Password');

    // add an ID attribute to the 2FA elements
    // this lets us then use CSS to style them
    $('a:contains("Cancel")').attr('id', 'cancel');
    $('button:contains("Next")').text('Sign In');
    $('button:contains("Sign In")').attr('id', 'next');

    // if the error list is visible, prepend the font-awesome icon
    $('.errorlist li').prepend('<i class="fa-solid fa-triangle-exclamation"></i> ');
});
