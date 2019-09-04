var CeleryProgressBar = (function () {
    function onSuccessDefault(progressBarElement, progressBarMessageElement) {
        progressBarElement.style.backgroundColor = '#76ce60';
        progressBarElement.style.width = 100 + "%";
        progressBarMessageElement.innerHTML = "Success!";
    }

    function onErrorDefault(progressBarElement, progressBarMessageElement) {
        progressBarElement.style.backgroundColor = '#dc4f63';
        progressBarMessageElement.innerHTML = "Uh-Oh, something went wrong!";
    }

    function onProgressDefault(progressBarElement, progressBarMessageElement, progress) {
        progressBarElement.style.backgroundColor = '#68a9ef';
        progressBarElement.style.width = progress.percent*100 + "%";
        progressBarMessageElement.innerHTML = progress.current + ' of ' + progress.total + ' processed.';
    }

    function updateProgress (progressUrl, options) {
        options = options || {};
        var progressBarId = options.progressBarId || 'progress-bar';
        var progressBarMessage = options.progressBarMessageId || 'progress-bar-message';
        var progressBarElement = options.progressBarElement || document.getElementById(progressBarId);
        var progressBarMessageElement = options.progressBarMessageElement || document.getElementById(progressBarMessage);
        var onProgress = options.onProgress || onProgressDefault;
        var onSuccess = options.onSuccess || onSuccessDefault;
        var onError = options.onError || onErrorDefault;
        var pollInterval = options.pollInterval || 2000;
        

        fetch(progressUrl).then(function(response) {
            response.json().then(function(data) {
                if (data.state === 'PROGRESS') {
                    onProgress(progressBarElement, progressBarMessageElement, data.details);
                }
                if (data.state !== 'COMPLETE') {
                    setTimeout(updateProgress, pollInterval, progressUrl, options);
                } 
                if (data.state === 'SUCCESS') {
                    onSuccess(progressBarElement, progressBarMessageElement);
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