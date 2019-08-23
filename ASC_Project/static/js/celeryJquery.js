
$(function () {
    var progressUrl = "{% url 'analyses:home' %}";
    CeleryProgressBar.initProgressBar(progressUrl)
  });