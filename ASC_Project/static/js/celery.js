var CeleryProgressBar = (function () {
    function onSuccessDefault(progressBarElement, progressBarMessageElement,gifElement) {
        progressBarElement.style.backgroundColor = '#76ce60';
        progressBarElement.style.width = 100 + "%";
        progressBarMessageElement.innerHTML = "Success!";
        gifElement.src='/static/success.gif/'
    }

    function onErrorDefault(progressBarElement, progressBarMessageElement) {
        progressBarElement.style.backgroundColor = '#dc4f63';
        progressBarMessageElement.innerHTML = "Uh-Oh, something went wrong!";
    }

    function onProgressDefault(progressBarElement, progressBarMessageElement, progress) {
        progressBarElement.style.backgroundColor = '#68a9ef';
        progressBarElement.style.width = progress.percent*100 + "%";
        progressBarMessageElement.innerHTML = 'Iteration: ' + progress.iteration + ', and ' + progress.fill_time + ' seconds of fill time has been passed.';
    }

    function updateProgress (progressUrl, options) {
        options = options || {};
        var progressBarId = options.progressBarId || 'progress-bar';
        var progressBarMessage = options.progressBarMessageId || 'progress-bar-message';
        var progressBarElement = options.progressBarElement || document.getElementById(progressBarId);
        var progressBarMessageElement = options.progressBarMessageElement || document.getElementById(progressBarMessage);
        var gifElement = document.getElementById('gif');
        var onProgress = options.onProgress || onProgressDefault;
        var onSuccess = options.onSuccess || onSuccessDefault;
        var onError = options.onError || onErrorDefault;
        var pollInterval = options.pollInterval || 2000;
        

        fetch(progressUrl).then(function(response) {
            response.json().then(function(data) {
                if (data.state === 'PROGRESS') {
                    onProgress(progressBarElement, progressBarMessageElement, data.details);
                }
                if (data.state !== 'SUCCESS') {
                    setTimeout(updateProgress, pollInterval, progressUrl, options);
                } 
                if (data.state === 'SUCCESS') {
                    onSuccess(progressBarElement, progressBarMessageElement, gifElement);
                } 
                
            });
        });
    }
    return {
        onSuccessDefault: onSuccessDefault,
        onErrorDefault: onErrorDefault,
        onProgressDefault: onProgressDefault,
        updateProgress: updateProgress,
        initProgressBar: updateProgress,  // just for api cleanliness
    };
})();