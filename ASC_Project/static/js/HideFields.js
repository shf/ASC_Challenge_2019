// Ideally this script (javascript code) would be in the HEAD of your page
// but if you put it at the bottom of the body (bottom of your template) that should be ok too.
// Also you need jQuery loaded but since you are using bootstrap that should
// be taken care of.  If not, you will have to deal with that.

    // function that hides/shows condition based upon typ value
    function check_field_value() {
        if($(this).find('select').val() === 'Wall') {
            $('#condition').hide();
            $('#value').hide();
        } else {
            $('#condition').show();
            $('#value').show();
        }
    }

    // this is executed once when the page loads
    $(document).ready(function() {
        // set things up so my function will be called when typ changes
        $('#typ').change(check_field_value);
        
        // set the state based on the initial values
        check_field_value.call($('#typ').get());
    });