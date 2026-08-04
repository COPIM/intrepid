
$( document ).ready(function() {
    // mirror the (translatable) field labels into the placeholders;
    // the login page renders desktop and mobile copies of the form, so
    // take only the first matching label
    $('#id_auth-username').attr('placeholder',
        $('label[for="id_auth-username"]').first().text().trim().replace(/:$/, ''));
    $('#id_auth-password').attr('placeholder',
        $('label[for="id_auth-password"]').first().text().trim().replace(/:$/, ''));

    // add an ID attribute to the 2FA elements
    // this lets us then use CSS to style them
    $('a:contains("Cancel")').attr('id', 'cancel');
    $('button:contains("Next")').text('Sign In');
    $('button:contains("Sign In")').attr('id', 'next');

    // if the error list is visible, prepend the font-awesome icon
    $('.errorlist li').prepend('<i class="fa-solid fa-triangle-exclamation"></i> ');
});
