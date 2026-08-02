!! Doclets: the browser client for a central, searchable Markdown document repository.
!!
!! Renders the Webson screen, talks to the doclet server over MQTT, and drives the topic / query / view / edit / save / delete workflow from a phone-sized UI.


    script Doclets

!    debug compile

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Doclet query system

!! @hash 22bcc580
!!!

!! Declare every DOM element and script variable up front.
!!
!! AllSpeak requires declarations before use; keeping them together lets the body code read as plain prose.

    div Body
    div TitleBanner
    div DebugRow
    div TopicList
    div TopicsDialogMask
    div TopicsDialogList
    div TopicItemTemplate
    div TopicItemTemplateRow
    div NewDocletDialogMask
    div NewDocletDialogList
    div NewTopicItemTemplate
    div DocletViewMask
    div DocletViewContent
    textarea DocletEditText
    div DocletListPanel
    button ChooseTopicsButton
    button SendQueryButton
    button NewDocletButton
    button TopicsDialogSelectAll
    button TopicsDialogDeselectAll
    button TopicsDialogOK
    button DocletViewEdit
    button DocletViewDelete
    button DocletViewSave
    button DocletViewClose
    button NewDocletCancel
    button NewTopicButton
    button DocletButton
    input QueryInput
    input TopicCheckbox
    button LLMQueryButton

    topic MyTopic
    topic ServerTopic
    variable Mac
    variable MyID
    variable Topics
    variable Query
    variable TopicsMarkup
    variable ResultsMarkup
    variable Text
    variable TopicItemMarkup
    variable Mobile
    variable State
    variable Action
    variable MessageText
    variable SaveRetry
    variable NewRetry
    variable DeleteRetry
    variable N
    variable P
    variable Config
    variable WaitCount
    variable ReceivedMessage
    variable TopicsAvailable
    variable TopicsListed
    variable TopicsSelected
    variable TopicsDisplayed
    variable TopicsReady
    variable DocletList
    variable CurrentDocletName
    variable SaveAuthToken
    variable DocletViewMode
    variable NewDocletTopic
    variable AutoStartEdit
    variable NewInFlight
    variable NewRequestID
    variable NewTopicButtonLabel
    variable DbgTapCount
    variable DbgLastTap
    variable DbgNow
    variable DbgRowVisible
    variable MaxWait
    variable LLMWaitLong

    variable MainScreenWebson

!    debug step

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Set up the UI

!    debug step

!   Set up MQTT
!! @hash 7d17c5d6
!!!

!! Boot sequence: load MQTT credentials (stored locally on localhost, fetched from the credentials endpoint elsewhere), connect to the broker, and hand control to the event handlers.
!!
!! The `on mqtt connect`, `on mqtt message` and `every 20 ticks` handlers drive the rest of the program; the save-button enable/disable poll lives here too.

    put `Doclets-` cat random 999999 into MyID
    log `MyID = ` cat MyID
    
    variable Credentials
    variable Broker
    variable Username
    variable Password
    variable NeedCredentials

    if the hostname is `localhost`
    begin
        get Broker from storage as `dev-broker`
        if Broker is `null` clear Broker
        if Broker is `undefined` clear Broker
        get Username from storage as `dev-username`
        if Username is `null` clear Username
        if Username is `undefined` clear Username
        get Password from storage as `dev-password`
        if Password is `null` clear Password
        if Password is `undefined` clear Password
        get Mac from storage as `dev-mac`
        if Mac is `null` clear Mac
        if Mac is `undefined` clear Mac
        clear NeedCredentials
        if Broker is empty set NeedCredentials
        if Mac is empty set NeedCredentials
        if NeedCredentials
        begin
            put prompt `Dev credentials:` cat newline cat `MQTT Broker URL:` into Broker
            put prompt `Dev credentials:` cat newline cat `Username:` into Username
            put prompt `Dev credentials:` cat newline cat `Password:` into Password
            put prompt `Dev credentials:` cat newline cat `Mac (MQTT request topic):` into Mac
            if Broker is empty go to AbandonShip
            put Broker into storage as `dev-broker`
            put Username into storage as `dev-username`
            put Password into storage as `dev-password`
            put Mac into storage as `dev-mac`
        end
    end
    else
    begin
        rest get Credentials from `https://doclets.eclecity.net/credentials.php`
            or go to AbandonShip
        put element `broker` of Credentials into Broker
        put element `username` of Credentials into Username
        put element `password` of Credentials into Password
        put element `mac` of Credentials into Mac
    end
    
    init ServerTopic
        name Mac
        qos 1

    init MyTopic
        name MyID
        qos 1

    mqtt
        token Username Password
        id MyID
        broker Broker
        port 443
        subscribe MyTopic

    on mqtt connect
    begin
        log `MQTT Connected`
        go to Connected
    end
    
    ! Handle incoming messages
    on mqtt message
    begin
        put the mqtt message into ReceivedMessage
    end

    ! Handle connection errors
    on mqtt error
    begin
        alert `MQTT connection failed: ` cat the mqtt error
            cat newline cat newline
            cat `This may be caused by:`
            cat newline cat `  - A server credentials issue`
            cat newline cat `  - A browser privacy setting (e.g. Brave Shields)`
            cat newline cat newline
            cat `Please refresh this page to try again.`
    end

    every 20 ticks
    begin
        if tracing stop
        if DocletViewMode is `edit`
        begin
            put DocletEditText into Text
            if Text is MessageText
            begin
                disable DocletViewSave
            end
            else
            begin
                enable DocletViewSave
            end
        end
    end
    stop

!! @hash 694fde33
!!!

!! On first connection: set up the main window, load any stored auth token, and ask the server for the list of topics the caller may read.

Connected:
    ! Do the basic setup of the main window
    put `idle` into State
    put empty into Topics
    put empty into ReceivedMessage
    clear TopicsReady
    set TopicsAvailable to array
    set TopicsSelected to array
    gosub to SetupScreen

    ! Load any stored auth token (no prompt) so private topics are listed
    get SaveAuthToken from storage as `save-auth-token`
    if SaveAuthToken is `null` clear SaveAuthToken
    if SaveAuthToken is `undefined` clear SaveAuthToken

    put `topics` into State
    send to ServerTopic
        sender MyTopic
        action `topics`
        message SaveAuthToken
    go to WaitForReply

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Set up the main screen
!! @hash 6d96cbe1
!!!

!! Render the Webson layout and attach every element the handlers will manipulate.
!!
!! Mobile devices get a full-width body, desktop a centred bordered card. All click handlers are registered once here.

SetupScreen:
    ! put SaveAuthToken into storage as `save-auth-token`
    log `Set up the screen...`

    set the title to `Doclet reader`

    clear Mobile
    if mobile
    begin
!    	log `Mobile browser detected`
        if portrait
        begin
!        	log `In portrait mode`
        	set Mobile
        end
    end
!    else log `PC browser detected`

	create Body
    if Mobile
    begin
    	set style `width` of Body to `100%`
        set style `overscroll-behavior-y` of Body to `none`
    end
    else
    begin
    	set style `width` of Body to `80vw`
        set style `margin` of Body to `0 auto`
        set style `border` of Body to `1px solid lightgray`
    end
    set style `height` of Body to `calc(100vh - 1em)`

!	Render the main screen layout
    rest get MainScreenWebson from `doclets.json?v=` cat now
    	or go to AbandonShip
	render MainScreenWebson in Body

    attach TitleBanner to `rbr-banner`
    attach DebugRow to `allspeak-tracer`
    attach TopicList to `TopicList`
    attach QueryInput to `QueryInput`
    attach LLMQueryButton to `LLMQueryButton`
    attach TopicsDialogMask to `TopicsDialogMask`
    attach TopicsDialogList to `TopicsDialogList`
    attach TopicItemTemplate to `TopicItemTemplate`
    attach TopicItemTemplateRow to `TopicItem-__SEQ__`
    attach NewDocletDialogMask to `NewDocletDialogMask`
    attach NewDocletDialogList to `NewDocletDialogList`
    attach NewTopicItemTemplate to `NewTopicItemTemplate`
    attach NewTopicButton to `NewTopicButton-__SEQ__`
    attach DocletViewMask to `DocletViewMask`
    attach DocletViewContent to `DocletViewContent`
    attach DocletEditText to `DocletEditTextarea`
    attach DocletListPanel to `DocletListPanel`
    attach ChooseTopicsButton to `ChooseTopicsButton`
    attach SendQueryButton to `SendQueryButton`
    attach NewDocletButton to `NewDocletButton`
    attach TopicsDialogSelectAll to `TopicsDialogSelectAllButton`
    attach TopicsDialogDeselectAll to `TopicsDialogDeselectAllButton`
    attach TopicsDialogOK to `TopicsDialogOKButton`
    attach DocletViewEdit to `DocletViewEditButton`
    attach DocletViewDelete to `DocletViewDeleteButton`
    attach DocletViewSave to `DocletViewSaveButton`
    attach DocletViewClose to `DocletViewCloseButton`
    attach NewDocletCancel to `NewDocletCancelButton`

    on click TitleBanner go to TitleBannerClick
    on click ChooseTopicsButton go to ChooseTopics
    on click SendQueryButton go to SendQueryClick
    on click LLMQueryButton go to LLMQueryClick
    on click NewDocletButton go to DocletViewNewClick
    on click TopicsDialogSelectAll go to TopicsDialogSelectAllClick
    on click TopicsDialogDeselectAll go to TopicsDialogDeselectAllClick
    on click TopicsDialogOK go to TopicsDialogOKClick
    on click DocletViewEdit go to DocletViewEditClick
    on click DocletViewDelete go to DocletViewDeleteClick
    on click DocletViewSave go to DocletViewSaveClick
    on click DocletViewClose go to DocletViewCloseClick
    on click NewDocletCancel go to NewDocletCancelClick
    on change DocletEditText go to DocletEditChanged

    enable QueryInput
    remove attribute `disabled` of QueryInput
    disable ChooseTopicsButton
    disable SendQueryButton
    clear SaveRetry
    clear NewRetry
    clear DeleteRetry
    clear AutoStartEdit
    clear NewInFlight
    clear NewRequestID

    set style `display` of DebugRow to `none`
    clear DbgTapCount
    clear DbgLastTap
    clear DbgRowVisible

    get TopicsDisplayed from storage as `topic-list`
    if TopicsDisplayed is `null` clear TopicsDisplayed
    if TopicsDisplayed is `undefined` clear TopicsDisplayed
    gosub to UpdateTopicsLabel
    gosub to UpdateSendButtonState
    split TopicsDisplayed on `,` into Topics
    put 0 into N
    while N is less than the elements of Topics
    begin
        index Topics to N
        if Topics is not empty
        begin
            json add Topics to TopicsSelected
        end
        add 1 to N
    end
    gosub to UpdateTopicsLabel
    log `Topics selected: ` cat TopicsSelected
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
! 	Warn the user and abandon this run
!! @hash 8a3ab478
!!!

!! Fatal-error exit: warn the user and abandon the run.

AbandonShip:
	alert `An unrecoverable error has occurred.`
    	cat newline cat `Please refresh this browser page to restart.`
    exit

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks the Choose button
!! @hash 98407b55
!!!

!! Open the topic picker: build the checkbox list from the available topics and restore the previously selected ones.

ChooseTopics:
    enable QueryInput
    if TopicsAvailable is empty set TopicsListed to array
    else json split TopicsAvailable on `,` into TopicsListed

    ! Build the topic list
    put empty into TopicsMarkup
    put 0 into N
    while N is less than json count of TopicsListed
    begin
        put item N of TopicsListed into Text
        put content of TopicItemTemplate into TopicItemMarkup
        replace `__SEQ__` with N in TopicItemMarkup
        replace `__VALUE__` with Text in TopicItemMarkup
        replace `__TEXT__` with Text in TopicItemMarkup
        put TopicsMarkup
            cat TopicItemMarkup
            into TopicsMarkup
        add 1 to N
    end
    set content of TopicsDialogList to TopicsMarkup

    ! Set the checkboxes
    set the elements of TopicCheckbox to json count of TopicsListed
    put 0 into N
    while N is less than elements of TopicCheckbox
    begin
        index TopicCheckbox to N
        attach TopicCheckbox to `TopicCheckbox-` cat N
        put item N of TopicsListed into Text
        if json index of Text in TopicsSelected is not -1
        begin
            set attribute `checked` of TopicCheckbox
        end
        add 1 to N
    end

    set style `display` of TopicsDialogMask to `flex`
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks a topic checkbox
!! @hash 8dd70b1e
!!!

!! Toggle a topic's membership in the selection as its checkbox changes.

TopicCheckboxClick:
    put index of TopicCheckbox into N
    put element N of TopicsAvailable into Text
    put json index of Text in TopicsSelected into P
    if P is less than 0
    begin
        json add Text to TopicsSelected
    end
    else
    begin
        json delete element P from TopicsSelected
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks Select All in the Choose dialog
!! @hash 35f62e41
!!!

!! Select every available topic in the picker.

TopicsDialogSelectAllClick:
    put 0 into N
    while N is less than elements of TopicCheckbox
    begin
        index TopicCheckbox to N
        set attribute `checked` of TopicCheckbox
        add 1 to N
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks Deselect All in the Choose dialog
!! @hash 3fae421f
!!!

!! Clear every checkbox in the picker.

TopicsDialogDeselectAllClick:
    put 0 into N
    while N is less than elements of TopicCheckbox
    begin
        index TopicCheckbox to N
        remove attribute `checked` of TopicCheckbox
        add 1 to N
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks the OK button in the Choose dialog
!! @hash b5257db6
!!!

!! Confirm the selection: rebuild the stored topic list and close the dialog.

TopicsDialogOKClick:
    enable QueryInput
    put empty into TopicsDisplayed
    set TopicsSelected to array
    put 0 into N
    while N is less than elements of TopicCheckbox
    begin
        index TopicCheckbox to N
        if TopicCheckbox
        begin
            put item N of TopicsListed into Text
            if TopicsDisplayed is not empty put TopicsDisplayed cat `,` into TopicsDisplayed
            put TopicsDisplayed cat Text into TopicsDisplayed
            json add Text to TopicsSelected
        end
        add 1 to N
    end
    gosub to UpdateTopicsLabel
    set style `display` of TopicsDialogMask to `none`
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks the Send button
!! @hash e1436bc5
!!!

!! Send a query to the server: plain text as-is, or prefixed with `LLM:` (and a much longer wait) for the AI button.
!!
!! The two button handlers share `DoQuerySend`, which also turns the query buttons amber while the request is in flight.

SendQueryClick:
    clear LLMWaitLong
    go to DoQuerySend

LLMQueryClick:
    set LLMWaitLong
    go to DoQuerySend

! Shared query send: LLM mode adds the `LLM:` prefix and a longer wait
DoQuerySend:
    enable QueryInput
    put QueryInput into Query
    if LLMWaitLong
    begin
        put `LLM:` cat Query into Query
    end
    put `query` into State
    clear DocletListPanel
    put empty into ReceivedMessage
    gosub to SetQueryWaiting
    log `Send ` cat Query
    send to ServerTopic
        sender MyTopic
        action `query`
        message SaveAuthToken cat newline cat TopicsDisplayed cat `|` cat Query
    go to WaitForReply

! Query-in-progress feedback: amber while waiting, red on failure
!! @hash c4653d25
!!!

!! Query-in-progress feedback: amber while waiting, red on failure, normal when a reply lands.

SetQueryWaiting:
    set style `background-color` of SendQueryButton to `#ffe08a`
    set style `background-color` of LLMQueryButton to `#ffe08a`
    disable SendQueryButton
    disable LLMQueryButton
    return

ResetQueryButtons:
    set style `background-color` of SendQueryButton to ``
    set style `background-color` of LLMQueryButton to ``
    enable SendQueryButton
    enable LLMQueryButton
    return

FailQueryButtons:
    set style `background-color` of SendQueryButton to `#ff9c9c`
    set style `background-color` of LLMQueryButton to `#ff9c9c`
    enable SendQueryButton
    enable LLMQueryButton
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks an item in the results list
!! @hash df5374e6
!!!

!! A result row was tapped: extract the doclet name and request its content.

ResultsListClick:
    put index of DocletButton into N
    put element N of DocletList into Query
    put the position of `:` in Query into P
    put left P of Query into Query
    put Query into CurrentDocletName
    put `content` into State
    put empty into ReceivedMessage
    send to ServerTopic
        sender MyTopic
        action `view`
        message SaveAuthToken cat newline cat Query
    go to WaitForReply

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Here when the user clicks the exit button
!! @hash e493caba
!!!

!! Log and exit (kept for completeness; the UI has no exit button).

ExitButtonClick:
!    set property `topics` of Config to the text of TopicsLabel
    log Config
!    save Config to ConfigFileName
    exit

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Wait for a reply. This may arrive in a different thread, so just save it
!! @hash 0d250e99
!!!

!! Poll for the reply to the outstanding request.
!!
!! LLM queries get a ~4 minute allowance (the first call loads the model); plain queries keep the ~10 second wait. A timeout turns the query buttons red.

WaitForReply:
    put 0 into WaitCount
    ! LLM queries need a much longer wait: the first call loads the model and
    ! embeds the topic (can take a minute), while plain queries answer in ~1s.
    if LLMWaitLong
    begin
        ! ~4 minutes: first LLM call after a restart loads the model (can be
        ! ~2 min on this hardware) plus generation.
        put 2400 into MaxWait
    end
    else
    begin
        put 100 into MaxWait
    end
    while ReceivedMessage is empty
    begin
        add 1 to WaitCount
        if WaitCount is greater than MaxWait
        begin
            log `Timeout waiting for response`
            clear LLMWaitLong
            gosub to FailQueryButtons
            enable QueryInput
            remove attribute `disabled` of QueryInput
            if State is `new`
            begin
                clear NewInFlight
                clear NewRequestID
                gosub to ResetNewTopicButtons
                enable NewDocletCancel
            end
            stop
        end
        wait 10 ticks
    end

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Process a received message
!! @hash f32efd03
!!!

!! Dispatch a received reply according to the current state: topics, query results, doclet content, or the new/save/delete confirmations.
!!
!! The ANSWER| prefix marks a prose (LLM synthesis) reply, rendered as a block rather than a button list.

ProcessMessage:
    gosub to ResetQueryButtons
    if State is `topics`
    begin
        if Action is `confirm` gosub to SendQueryButtonConfirmation
!        log `Topics available: ` cat ReceivedMessage
        put ReceivedMessage into storage as `topics-available`
        put ReceivedMessage into TopicsAvailable
        set TopicsReady
        gosub to UpdateTopicsLabel
        enable QueryInput
        enable ChooseTopicsButton
        gosub to UpdateSendButtonState
    end
    else if State is `query`
    begin
        enable QueryInput
        if left 7 of ReceivedMessage is `ANSWER|`
        begin
            ! `from N of` is 0-based (substr), so 7 skips the 7-char `ANSWER|` marker.
            put from 7 of ReceivedMessage into Text
            replace newline with `<br>` in Text
            set content of DocletListPanel to `<div style='padding:1em;font-size:1.05em;line-height:1.5;word-wrap:break-word;'>` cat Text cat `</div>`
            stop
        end
        if ReceivedMessage is `[]`
        begin
            set content of DocletListPanel to `<div style='font-size:1.3em;font-weight:bold;text-align:center;padding-top:1em;'>No matching doclets</div>`
            stop
        end
        put ReceivedMessage into DocletList
        log DocletList

        put empty into ResultsMarkup
        put 0 into N
        while N is less than json count of DocletList
        begin
            put element N of DocletList into Text
            put the position of `:` in Text into P
            if P is greater than -1
            begin
                put left P of Text into Query
                add 1 to P
                put Query cat `<br>` cat from P of Text into Text
            end
            put ResultsMarkup
                cat `<button id='DocletButton-` cat N cat `' style='display:block;width:100%;text-align:left;margin-bottom:0.3em;'>`
                cat Text
                cat `</button>`
                into ResultsMarkup
            add 1 to N
        end
        set content of DocletListPanel to ResultsMarkup

        set the elements of DocletButton to json count of DocletList
        put 0 into N
        while N is less than elements of DocletButton
        begin
            index DocletButton to N
            attach DocletButton to `DocletButton-` cat N
            add 1 to N
        end
        on click DocletButton go to ResultsListClick
    end
    else if State is `content`
    begin
        enable QueryInput
        put the position of `Error reading file:` in ReceivedMessage into P
        if P is greater than -1
        begin
            alert ReceivedMessage
            stop
        end
        if left 8 of ReceivedMessage is `Created `
        begin
            if CurrentDocletName is not empty
            begin
                put empty into ReceivedMessage
                send to ServerTopic
                    sender MyTopic
                    action `view`
                    message SaveAuthToken cat newline cat CurrentDocletName
                go to WaitForReply
            end
            stop
        end
        put ReceivedMessage into MessageText
        put `view` into DocletViewMode
        set style `display` of DocletEditText to `none`
        set style `display` of DocletViewContent to `block`
        set attribute `data-markdown` of DocletViewContent to `1`
        set content of DocletViewContent to MessageText
        scroll DocletViewContent to 0
        set content of DocletViewEdit to `Edit`
        enable DocletViewEdit
        enable DocletViewDelete
        set style `display` of DocletViewDelete to `block`
        disable DocletViewSave
        set style `display` of DocletViewSave to `none`
        set style `display` of DocletViewMask to `flex`
        if AutoStartEdit
        begin
            clear AutoStartEdit
            gosub to DocletViewEditClick
        end
    end
    else if State is `new`
    begin
        clear NewInFlight
        gosub to ResetNewTopicButtons
        enable NewDocletCancel
        enable QueryInput
        put ReceivedMessage into MessageText
        if left 8 of MessageText is `Created `
        begin
            if SaveAuthToken is not empty
            begin
                put SaveAuthToken into storage as `save-auth-token`
            end
            clear NewRequestID
            put MessageText into CurrentDocletName
            replace `Created ` with empty in CurrentDocletName
            set style `display` of NewDocletDialogMask to `none`
            set style `display` of TopicsDialogMask to `none`
            set style `display` of DocletViewMask to `none`
            set AutoStartEdit
            put `content` into State
            put empty into ReceivedMessage
            send to ServerTopic
                sender MyTopic
                action `view`
                message SaveAuthToken cat newline cat CurrentDocletName
            go to WaitForReply
        end
        else
        begin
            put the position of `unauthorized` in MessageText into P
            if P is greater than -1
            begin
                clear SaveAuthToken
                remove `save-auth-token` from storage
                if NewRetry is 0
                begin
                    put 1 into NewRetry
                    gosub to EnsureSaveAuthToken
                    if SaveAuthToken is empty
                    begin
                        alert `Create denied and no new token entered; create cancelled`
                        stop
                    end
                    put empty into ReceivedMessage
                    send to ServerTopic
                        sender MyTopic
                        action `new`
                        message SaveAuthToken cat newline cat NewDocletTopic cat newline cat NewRequestID
                    go to WaitForReply
                end
            end
            clear NewRequestID
            alert MessageText
        end
    end
    else if State is `save`
    begin
        enable QueryInput
        put ReceivedMessage into MessageText
        put the position of `Saved ` in MessageText into P
        if P is greater than -1
        begin
            if SaveAuthToken is not empty
            begin
                put SaveAuthToken into storage as `save-auth-token`
            end
            ! Refresh the current result set so list entries reflect saved changes
            alert MessageText
            go to SendQueryClick
        end
        put the position of `unauthorized` in MessageText into P
        if P is greater than -1
        begin
            clear SaveAuthToken
            remove `save-auth-token` from storage
            if SaveRetry is 0
            begin
                put 1 into SaveRetry
                gosub to EnsureSaveAuthToken
                if SaveAuthToken is empty
                begin
                    disable DocletViewSave
                    enable DocletViewEdit
                    alert `Save denied and no new token entered; save cancelled`
                    stop
                end
                put DocletEditText into MessageText
                put empty into ReceivedMessage
                send to ServerTopic
                    sender MyTopic
                    action `save`
                    message SaveAuthToken cat newline cat CurrentDocletName cat newline cat MessageText
                go to WaitForReply
            end
        end
        disable DocletViewSave
        enable DocletViewEdit
        alert MessageText
    end
    else if State is `delete`
    begin
        enable QueryInput
        put ReceivedMessage into MessageText
        put the position of `Deleted ` in MessageText into P
        if P is greater than -1
        begin
            if SaveAuthToken is not empty
            begin
                put SaveAuthToken into storage as `save-auth-token`
            end
            alert MessageText
            gosub to CloseDocletView
            go to SendQueryClick
        end

        put the position of `unauthorized` in MessageText into P
        if P is greater than -1
        begin
            clear SaveAuthToken
            remove `save-auth-token` from storage
            if DeleteRetry is 0
            begin
                put 1 into DeleteRetry
                gosub to EnsureSaveAuthToken
                if SaveAuthToken is empty
                begin
                    alert `Delete denied and no new token entered; delete cancelled`
                    stop
                end
                put empty into ReceivedMessage
                send to ServerTopic
                    sender MyTopic
                    action `delete`
                    message SaveAuthToken cat newline cat CurrentDocletName
                go to WaitForReply
            end
        end
        alert MessageText
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Switch the doclet view into edit mode
!! @hash d72c7cab
!!!

!! Toggle the doclet view between read mode and the edit textarea.

DocletViewEditClick:
    if DocletViewMode is `view`
    begin
        put `edit` into DocletViewMode
        set content of DocletViewEdit to `View`
        set style `display` of DocletViewContent to `none`
        set style `display` of DocletEditText to `block`
        set content of DocletEditText to MessageText
        set style `display` of DocletViewDelete to `none`
        disable DocletViewDelete
        set style `display` of DocletViewSave to `block`
        disable DocletViewSave
    end
    else
    begin
        put `view` into DocletViewMode
        set content of DocletViewEdit to `Edit`
        put DocletEditText into MessageText
        set style `display` of DocletEditText to `none`
        set style `display` of DocletViewContent to `block`
        set attribute `data-markdown` of DocletViewContent to `1`
        set content of DocletViewContent to MessageText
        set style `display` of DocletViewDelete to `block`
        enable DocletViewDelete
        set style `display` of DocletViewSave to `none`
        disable DocletViewSave
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Enable Save only when edit content differs from baseline MessageText
!! @hash 3d344857
!!!

!! Enable Save only when the edit buffer differs from the last-loaded content.

DocletEditChanged:
    if DocletViewMode is `edit`
    begin
        put DocletEditText into Text
        if Text is MessageText
        begin
            disable DocletViewSave
        end
        else
        begin
            enable DocletViewSave
        end
    end
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Open the New doclet topic picker dialog
!! @hash 5ea7d9fc
!!!

!! Open the new-doclet picker: choose a topic, or create directly when only one topic is selected.

DocletViewNewClick:
    gosub to EnsureSaveAuthToken
    if SaveAuthToken is empty
    begin
        alert `No authorization token entered; create cancelled`
        stop
    end

    if TopicsSelected is empty
    begin
        alert `No topics are selected`
        stop
    end

    clear NewInFlight
    clear NewRequestID
    enable NewDocletCancel

    if json count of TopicsSelected is 1
    begin
        put element 0 of TopicsSelected into NewDocletTopic
        go to NewDocletCreateClick
    end

    put empty into TopicsMarkup
    put 0 into N
    while N is less than json count of TopicsSelected
    begin
        put element N of TopicsSelected into Text
        put content of NewTopicItemTemplate into TopicItemMarkup
        replace `__SEQ__` with N in TopicItemMarkup
        replace `__VALUE__` with Text in TopicItemMarkup
        replace `__TEXT__` with Text in TopicItemMarkup
        put TopicsMarkup cat TopicItemMarkup into TopicsMarkup
        add 1 to N
    end
    set content of NewDocletDialogList to TopicsMarkup

    set the elements of NewTopicButton to json count of TopicsSelected
    put 0 into N
    while N is less than elements of NewTopicButton
    begin
        index NewTopicButton to N
        attach NewTopicButton to `NewTopicButton-` cat N
        put element N of TopicsSelected into NewTopicButtonLabel
        set text of NewTopicButton to NewTopicButtonLabel
        enable NewTopicButton
        set style `opacity` of NewTopicButton to `1`
        add 1 to N
    end
    on click NewTopicButton go to NewTopicButtonClick

    set style `display` of NewDocletDialogMask to `flex`
    stop

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Create immediately when a topic button is tapped
!! @hash 2b6d12d7
!!!

!! Create in the tapped topic immediately, disabling the other topic buttons while the request is in flight.

NewTopicButtonClick:
    if NewInFlight stop
    put index of NewTopicButton into N
    put element N of TopicsSelected into NewDocletTopic
    put 0 into P
    while P is less than elements of NewTopicButton
    begin
        index NewTopicButton to P
        disable NewTopicButton
        if P is N
        begin
            set text of NewTopicButton to `Creating...`
            set style `opacity` of NewTopicButton to `1`
        end
        else
        begin
            set style `opacity` of NewTopicButton to `0.65`
        end
        add 1 to P
    end
    disable NewDocletCancel
    go to NewDocletCreateClick

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Cancel New doclet creation
!! @hash 052c69e8
!!!

!! Cancel a pending new-doclet creation and restore the topic buttons.

NewDocletCancelClick:
    clear NewInFlight
    clear NewRequestID
    gosub to ResetNewTopicButtons
    enable NewDocletCancel
    set style `display` of NewDocletDialogMask to `none`
    stop

!! @hash 1724f77d
!!!

!! Restore the new-doclet topic buttons to their idle labels.

ResetNewTopicButtons:
    put 0 into P
    while P is less than elements of NewTopicButton
    begin
        index NewTopicButton to P
        put element P of TopicsSelected into NewTopicButtonLabel
        set text of NewTopicButton to NewTopicButtonLabel
        enable NewTopicButton
        set style `opacity` of NewTopicButton to `1`
        add 1 to P
    end
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Create a New doclet in the selected topic
!! @hash 11f9cf0e
!!!

!! Send the create request with a fresh request id, remembering the in-flight state.

NewDocletCreateClick:
    if NewInFlight stop
    if NewDocletTopic is empty
    begin
        if json count of TopicsSelected is 0
        begin
            alert `No topics are selected`
            stop
        end
        put element 0 of TopicsSelected into NewDocletTopic
    end
    put `new-` cat random 999999999 into NewRequestID
    set NewInFlight
    disable NewDocletCancel
    put 0 into NewRetry
    put `new` into State
    put empty into ReceivedMessage
    send to ServerTopic
        sender MyTopic
        action `new`
        message SaveAuthToken cat newline cat NewDocletTopic cat newline cat NewRequestID
    go to WaitForReply

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Save edited doclet content
!! @hash bb61fdab
!!!

!! Send the edited content to the server for saving.

DocletViewSaveClick:
    gosub to EnsureSaveAuthToken
    if SaveAuthToken is empty
    begin
        alert `No authorization token entered; save cancelled`
        stop
    end
    put DocletEditText into MessageText
    put `save` into State
    put empty into ReceivedMessage
    send to ServerTopic
        sender MyTopic
        action `save`
        message SaveAuthToken cat newline cat CurrentDocletName cat newline cat MessageText
    go to WaitForReply

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Delete current doclet from prettified view
!! @hash f34016aa
!!!

!! Confirm and request deletion of the current doclet.

DocletViewDeleteClick:
    put confirm `Delete ` cat CurrentDocletName cat ` ?` into Text
    if Text is empty stop

    gosub to EnsureSaveAuthToken
    if SaveAuthToken is empty
    begin
        alert `No authorization token entered; delete cancelled`
        stop
    end

    put 0 into DeleteRetry
    put `delete` into State
    put empty into ReceivedMessage
    send to ServerTopic
        sender MyTopic
        action `delete`
        message SaveAuthToken cat newline cat CurrentDocletName
    go to WaitForReply

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Close the doclet view popup
!! @hash dbb10d00
!!!

!! Close the doclet view popup.

DocletViewCloseClick:
    gosub to CloseDocletView
    stop

!! @hash 3d7933ce
!!!

!! Restore the view popup to its idle state.

CloseDocletView:
    enable QueryInput
    put `view` into DocletViewMode
    set content of DocletViewEdit to `Edit`
    disable DocletViewEdit
    disable DocletViewDelete
    set style `display` of DocletViewDelete to `block`
    disable DocletViewSave
    set style `display` of DocletViewSave to `none`
    set style `display` of DocletEditText to `none`
    set style `display` of DocletViewContent to `block`
    set style `display` of DocletViewMask to `none`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Set the text of the topics label
!! @hash 579f3953
!!!

!! Refresh the topics label and the send-button state after any selection change.

UpdateTopicsLabel:
    if TopicsDisplayed is `null` clear TopicsDisplayed
    if TopicsDisplayed is `undefined` clear TopicsDisplayed
    if TopicsDisplayed is empty
    begin
        set content of TopicList to `No topics chosen`
        set style `color` of TopicList to `#800`
    end
    else
    begin
        if TopicsReady
        begin
            if json count of TopicsSelected is json count of TopicsAvailable
            begin
                set content of TopicList to `All topics chosen`
                set style `color` of TopicList to `#080`
            end
            else
            begin
                set content of TopicList to `Topics: ` cat TopicsDisplayed
                set style `color` of TopicList to `inherit`
            end
        end
        else
        begin
            set content of TopicList to `Topics: ` cat TopicsDisplayed
            set style `color` of TopicList to `inherit`
        end
    end
    put TopicsDisplayed into storage as `topic-list`
    gosub to UpdateSendButtonState
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Enable Send only when topics have loaded and at least one topic is chosen
!! @hash d6fbe33b
!!!

!! Send is enabled only when topics have loaded and at least one is chosen.

UpdateSendButtonState:
    if TopicsReady
    begin
        if TopicsDisplayed is empty disable SendQueryButton
        else enable SendQueryButton
    end
    else
    begin
        disable SendQueryButton
    end
    return

! Send a confirmation message
!! @hash cef7aa8d
!!!

!! Send a confirm action back to the server (part of the topics handshake).

SendConfirmation:
    send to ServerTopic
        sender MyTopic
        action `confirm`
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Triple-tap title to show/hide the tracer panel
!! @hash fcc915f8
!!!

!! Triple-tap the title to show or hide the debug/tracer panel.

TitleBannerClick:
    put now into DbgNow
    ! Handle both second-based and millisecond-based now values
    if DbgNow is greater than 10000000000 put 3000 into P
    else put 3 into P

    if DbgLastTap is empty
    begin
        put 1 into DbgTapCount
    end
    else
    begin
        put DbgNow into N
        take DbgLastTap from N
        if N is greater than P put 1 into DbgTapCount
        else add 1 to DbgTapCount
    end

    put DbgNow into DbgLastTap
    if DbgTapCount is greater than 2
    begin
        clear DbgTapCount
        gosub to ToggleDebugRow
    end
    stop

!! @hash 06176d39
!!!

!! Show or hide the tracer row.

ToggleDebugRow:
    if DbgRowVisible
    begin
        clear DbgRowVisible
        clear DebugRow
        set style `display` of DebugRow to `none`
    end
    else
    begin
        set DbgRowVisible
        set style `display` of DebugRow to `block`
    end
    return

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   Ensure we have a save auth token (stored locally, prompt only if missing)
!! @hash 7e467b8b
!!!

!! Fetch the saved auth token, prompting for one only when none is stored.

EnsureSaveAuthToken:
    get SaveAuthToken from storage as `save-auth-token`
    if SaveAuthToken is `null` clear SaveAuthToken
    if SaveAuthToken is `undefined` clear SaveAuthToken
    if SaveAuthToken is empty
    begin
        put prompt `Enter save authorization token` into SaveAuthToken
        if SaveAuthToken is `null` clear SaveAuthToken
        if SaveAuthToken is `undefined` clear SaveAuthToken
        if SaveAuthToken is not empty
        begin
            put trim SaveAuthToken into SaveAuthToken
        end
    end
    return
!! @hash 1edc40f5
!!!
