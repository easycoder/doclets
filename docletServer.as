!! Doclet server: the server half of Doclets, run under the AllSpeak Python runtime.
!!
!! Loads MQTT credentials, subscribes to the request topic, and delegates each incoming action to the `doclets` plugin.


    script DocletServer

    use mqtt
    use plugin Doclets from as_doclets.py

    topic ServerTopic
    topic SenderTopic
    dictionary Sender
    dictionary ReceivedMessage
    list ResultList
    list TopicsList
    queue MessageQueue
    variable Credentials
    variable Broker
    variable Username
    variable Password
    variable MyID
    variable SenderName
    variable Topics
    variable Action
    variable SenderQoS
    variable MessageText
    dictionary CredDict

!    debug step

    ! Get MQTT credentials
!! @hash a35f78fb
!!!

!! Load MQTT credentials from a local file if present, otherwise fetch them from the credentials endpoint.

    if file `credentials` exists load Credentials from `credentials`
    else
    begin
	    get Credentials from url `https://doclets.eclecity.net/credentials.php`
    	    or go to NoCredentials
    end
    put json Credentials into CredDict
    put entry `broker` of CredDict into Broker
    put entry `username` of CredDict into Username
    put entry `password` of CredDict into Password
    put entry `mac` of CredDict into MyID

    log `Broker is ` cat Broker
    log `Username is ` cat Username
    log `Password is ` cat Password
    log `MyID is ` cat MyID

    ! Set up MQTT
!! @hash bc2ca66a
!!!

!! Connect to the broker, subscribe, and run the request/reply loop.
!!
!! Each message is popped and dispatched by action; the doclets plugin does the heavy lifting.

    init ServerTopic
        name MyID
        qos 1

    mqtt
        token Username Password
        id uuid
        broker Broker
        port 8883
        subscribe ServerTopic

    doclets init
    
    on mqtt message append the mqtt message to MessageQueue

    while true
    begin
        wait 50 ticks
        if MessageQueue is not empty
        begin
            pop ReceivedMessage from MessageQueue
            put entry `sender` of ReceivedMessage into Sender
            put entry `action` of ReceivedMessage into Action
            put entry `message` of ReceivedMessage into MessageText
            put entry `name` of Sender into SenderName
            put entry `qos` of Sender into SenderQoS

            if Action is `topics` gosub to GetTopics
            else if Action is `query` gosub to DoQuery
            else if Action is `view` gosub to GetDoclet
            else if Action is `save` gosub to HandleSaveViaPlugin
            else if Action is `new` gosub to HandleNewViaPlugin
            else if Action is `delete` gosub to HandleDeleteViaPlugin
        end
    end
    stop

! Get a list of the available doclet topics
!! @hash c388fe7a
!!!

!! Reply with the topics the requester may read (the plugin filters by the caller's token).

GetTopics:
    doclets topics TopicsList from ReceivedMessage
    put TopicsList into MessageText
    go to SendReply

! Process a query
!! @hash 66c8648b
!!!

!! Search for doclets matching the query and send the result list back.

DoQuery:
    doclets query ResultList from ReceivedMessage
    if the count of ResultList is 0 log `No results`
    else log `Sending ` cat left 40 of ResultList
    put ResultList into MessageText
    go to SendReply

! Get the content of a doclet
!! @hash e3dc6957
!!!

!! Read one doclet's content and reply.

GetDoclet:
    doclets view MessageText from ReceivedMessage
    go to SendReply

! Save handling is delegated to as_doclets.py (ACL + path validation + file write)
!! @hash 958e08e8
!!!

!! Save handling is delegated to as_doclets.py (ACL + path validation + file write).

HandleSaveViaPlugin:
    doclets save MessageText from ReceivedMessage
    go to SendReply

! New doclet handling is delegated to as_doclets.py
!! @hash e12d8581
!!!

!! New doclet handling is delegated to as_doclets.py.

HandleNewViaPlugin:
    doclets new MessageText from ReceivedMessage
    go to SendReply

! Delete doclet handling is delegated to as_doclets.py
!! @hash 44bcb26a
!!!

!! Delete handling is delegated to as_doclets.py.

HandleDeleteViaPlugin:
    doclets delete MessageText from ReceivedMessage
    go to SendReply

! Send a reply message
!! @hash 329535d5
!!!

!! Send a reply message back to the sender's own topic.

SendReply:
    init SenderTopic
        name SenderName
        qos SenderQoS
    set Action to `reply`
    send to SenderTopic
        action Action
        message MessageText
    return

!! @hash fb257dfe
!!!

!! Credentials could not be obtained: report and exit.

NoCredentials:
    print `Failed to get MQTT credentials from server.`
    exit
!! @hash 539b739d
!!!
