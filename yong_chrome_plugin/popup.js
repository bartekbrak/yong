$(document).ready(function() {
    console.log('YONG: start');

    chrome.tabs.query({'active': true, 'currentWindow': true}, function (tabs) {
        $('#url').val(tabs[0].url);
    });
    $(document).keypress(function(e) {
        if(e.which == 13) {
            $("button").click();
            e.preventDefault();
        }
    });
    chrome.identity.getProfileUserInfo(function(userInfo) {
        // https://stackoverflow.com/a/28984616/1472229
        $('#who').val(userInfo.email);
        if (userInfo.email != "") $('#who').attr('readonly', true).attr('tabindex', 7);
    });
    chrome.storage.sync.get(['key'], function(result) {
        // https://developer.chrome.com/extensions/storage#type-StorageArea
        console.log('Server currently is ' + result.key);
        if (result.key != "" && result.key !== undefined) {
            $('#server').val(result.key);
        } else {
            $('#server').val("http://yong.brak.me/");
        }
    });
    $('input').blur(function() {
         if(!$.trim(this.value).length) {
            $(this).addClass('warning');
         } else {
            $(this).removeClass('warning');
         }
    });
    $()
    $('#open').click(function(e){
        // https://stackoverflow.com/a/19851803/1472229
        if ( !$('#url').val()) return
        var win = window.open($('#url').val(), '_blank');
        if (win) {
            win.focus();
        } else {
            // Browser blocked it
            $("#info").html('Please allow popups for this website');
        }
    });
    $('button').click(function(e) {
        $('button').prop("disabled",true);
        $(this).html('...');

        if (! ($('#server').val() && $('#cats').val() && $('#mark').val() && $('#url').val() && $('#who').val())) {
            $("#info").html('missing values');
            $('button').prop("disabled", false);
            $("input").each(function() {
                if ($(this).attr('id') == "desc") return true;
                if ($(this).val() == "") {
                    $(this).addClass('warning');
                } else {
                    $(this).removeClass('warning');
                }
            });
            $(this).html('send');

            return
        }
        $.ajax({
            type: "POST",
            url: $('#server').val(),
            data: JSON.stringify({
                cats: $('#cats').val(),
                desc: $('#desc').val(),
                mark: $('#mark').val(),
                url:  $('#url').val(),
                who:  $('#who').val()
            }),
            contentType: 'application/json',
            success: function() { $("#info").html('sent'); },
            dataType: 'json'
        })
        .done(function() {
            $("#info").html('done');
               chrome.storage.sync.set({key: $('#server').val()}, function() {
                   console.log('server set to ' + $('#server'));
               });
            setTimeout(function () {
                $("#info").html('will close in 3 seconds.');
                setTimeout(function () { $("#info").html('will close in 2 seconds.'); }, 1000);
                setTimeout(function () { $("#info").html('will close in 1 second.'); }, 2000);
                setTimeout(function () { window.close(); }, 3000);
            }, 2000);

        })
        .fail(function(problem, z) {
            $("#info").html('fail, see console log');
            console.log(problem);
            console.log(z);
            $("#info").html('missing values');
            $('button').prop("disabled", false);
        })
    });
});
