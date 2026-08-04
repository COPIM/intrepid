
$( document ).ready(function() {
    // mirror the (translatable) field labels into the placeholders
    $('#id_auth-username').attr('placeholder',
        $('label[for="id_auth-username"]').text().trim().replace(/:$/, ''));
    $('#id_auth-password').attr('placeholder',
        $('label[for="id_auth-password"]').text().trim().replace(/:$/, ''));

    // add an ID attribute to the 2FA elements
    // this lets us then use CSS to style them
    $('a:contains("Cancel")').attr('id', 'cancel');
    $('button:contains("Next")').text('Sign In');
    $('button:contains("Sign In")').attr('id', 'next');

    // if the error list is visible, prepend the font-awesome icon
    $('.errorlist li').prepend('<i class="fa-solid fa-triangle-exclamation"></i> ');
});
